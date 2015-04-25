// dependencies
var async = require('async');
var AWS = require('aws-sdk');
var gm = require('gm').subClass({ imageMagick: true }); // Enable ImageMagick integration.
var util = require('util');

// constants
// var MAX_WIDTH  = 100;
// var MAX_HEIGHT = 100;

// get reference to S3 client 
var s3 = new AWS.S3();
 
exports.handler = function(event, context) {
	// Read options from the event.
	console.log("Reading options from event:\n", util.inspect(event, {depth: 5}));
	var srcBucket = event.Records[0].s3.bucket.name;
	// Object key may have spaces or unicode non-ASCII characters.
    var srcKey    = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, " "));  
	var dstBucket = srcBucket + "-thumbnail";
	// var dstKey    = "thumb-" + srcKey;

	// Sanity check: validate that source and destination are different buckets.
	if (srcBucket == dstBucket) {
		console.error("Destination bucket must not match source bucket.");
		return;
	}

	// Infer the image type.
	var typeMatch = srcKey.match(/\.([^.]*)$/);
	if (!typeMatch) {
		console.error('unable to infer image type for key ' + srcKey);
		return;
	}
	var imageType = typeMatch[1];
	if (imageType != "jpg" && imageType != "jpeg" && imageType != "png" && imageType != "gif") {
		console.log('skipping non-image ' + srcKey);
		return;
	}

	var filenameMatch = srcKey.match(/(.*)(\.[^.]*)$/);
	if (!filenameMatch) {
		console.error('unable to find the filename for key ' + srcKey);
		return;
	}
	var keyPrefix = filenameMatch[1];
	var keyExtension = filenameMatch[2];

	var contentType;

	var s3GetParams = {
		Bucket: srcBucket,
		Key: srcKey
	};

	var thumbnailAndUpload = async.seq(
		function thumbnail(newSizePx, gmObj, isLandscape, next) {
			var resized;

			if (isLandscape) {
				resized = gmObj.resize(newSizePx, null, '>');
			} else {
				resized = gmObj.resize(null, newSizePx, '>');
			}

			var newKey = keyPrefix + '_S' + newSizePx.toString() + keyExtension;
			resized.toBuffer(imageType, function(err, buffer) {
					if (err) {
						next(err);
					} else {
						next(null, newKey, buffer);
					}
				});

			},
		function upload(newKey, buffer, next) {
			// Stream the transformed image to a different S3 bucket.
			s3.putObject({
					Bucket: dstBucket,
					Key: newKey,
					Body: buffer,
					ContentType: contentType,
					ACL: 'public-read',
					StorageClass: 'REDUCED_REDUNDANCY',
				},
				function(err, data) {
					if (err) {
						next(err);
					} else {
						next(null, {AWSResponseData: data, 
								   	Bucket: dstBucket,
									Key: newKey });
					}
				});
			}
	);
	
	// Download the image from S3, transform, and upload to a different S3 bucket.
	async.waterfall([
		function download(next) {
			s3.getObject(s3GetParams, next);
		},
		function makeGM(response, next) {
			contentType = response.ContentType;  // contentType from above (function global)
			gm(response.Body).autoOrient().size(function(err, size) {
				if (err) {
					next(err);
				} else {
					var isLandscape = false;
					if (size.width > size.height) {
						isLandscape = true;
					}
					next(null, this, isLandscape);
				}

			});
		},
		function doIt(gmObj, isLandscape, next) {
			async.parallel({
					48: function(callback) {thumbnailAndUpload(48, gmObj, isLandscape, callback);},
					100: function(callback) {thumbnailAndUpload(100, gmObj, isLandscape, callback);},
					144: function(callback) {thumbnailAndUpload(144, gmObj, isLandscape, callback);},
					205: function(callback) {thumbnailAndUpload(205, gmObj, isLandscape, callback);},
					320: function(callback) {thumbnailAndUpload(320, gmObj, isLandscape, callback);},
					610: function(callback) {thumbnailAndUpload(610, gmObj, isLandscape, callback);},
					960: function(callback) {thumbnailAndUpload(960, gmObj, isLandscape, callback);},
				},
				next);
		},
		function finalizeResults(results, next) {
			console.log("Got doIt parallel results of :\n", util.inspect(results, {depth: 5}));
			var queue = null;
			
			if (srcKey.indexOf('dev') === 0) {
				queue = "https://sqs.us-east-1.amazonaws.com/435327525078/media-img-thumbnail-dev";
			}
			if (queue) {
				var msg = {	type: 'createThumbnail', 
							srcKey: srcKey, 
							srcBucket: srcBucket, 
							thumbnailResults: results};
				var sqs = new AWS.SQS({endpoint: "https://sqs.us-east-1.amazonaws.com"});
				sqs.sendMessage({
					QueueUrl: queue,
					MessageBody: JSON.stringify(msg),
				}, next);
			} else {
				console.warn('No SQS queue established for srcKey ' + srcKey, ', no message sent to SQS.');
				next();
			}
			
		}
		], function (err, sqsdata) {
			if (err) {
				console.error(
					'Unable to resize ' + srcBucket + '/' + srcKey +
					' and upload to ' + dstBucket + '/' + keyPrefix +
					' due to an error: ' + err
				);
			} else {
				console.log(
					'Successfully resized ' + srcBucket + '/' + srcKey +
					' and uploaded to ' + dstBucket + '/' + keyPrefix + '_SXXX' + keyExtension
				);
				if (sqsdata) {
					console.log("SQS MessageId: " + sqsdata.MessageId);
				}
			}

			context.done();
		}
	);
};
