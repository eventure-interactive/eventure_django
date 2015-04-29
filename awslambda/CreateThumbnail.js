// dependencies
var async = require('async');
var AWS = require('aws-sdk');
var gm = require('gm').subClass({ imageMagick: true }); // Enable ImageMagick integration.
var util = require('util');
var uuid  = require('node-uuid');

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
				resized = gmObj.resize(newSizePx, null, '>');  // '>' ensures we will resize only if we are downsizing (wont upscale)
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
		function getNewSize(newKey, buffer, next) {
			// the 'resized' var in thubmnail above keeps gmObj's size characteristics even after the resize (pre-resize),
			// so make a new object here to get the dimensions.
			gm(buffer).size(function(err, size){
				if (err){
					next(err);
				} else {
					next(null, newKey, buffer, size.width, size.height);
				}
			});
			},
		function upload(newKey, buffer, width, height, next) {
			var newUrl = "https://" + dstBucket + ".s3.amazonaws.com/" +  newKey;
			// Stream the transformed image to a different S3 bucket.
			var req = s3.putObject({
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
						var sizeBytes = req.httpRequest.headers['Content-Length'];
						next(null, { // AWSResponseData: data,  // excluding this, as the Etag is formatted with escaped quotes,
																// and we don't need anything in this right now.
									Bucket: dstBucket,
									Key: newKey,
									SizeBytes:  sizeBytes,
									Width: width,
									Height: height,
									Url: newUrl});
					}
				});
			}
	);
	
	// Download the image from S3, transform, and upload to a different S3 bucket.
	async.waterfall([
		function download(next) {
			s3.getObject(s3GetParams, next);
		},
		function makeGraphicsMagic(response, next) {
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
		function downsample(gmObj, isLandscape, next) {
			// Downsample potentially very large images so that we are at most dealing with a 1280 px image
			// and we don't have to keep around response.Body from above.
			// This step can result in quite large time and memory savings.
			gmObj.resize(1280, 1280, '>').toBuffer(imageType, function(err, buffer) {
					if (err) {
						next(err);
					} else {
						next(null, buffer, isLandscape);
					}
				});
		},
		function doIt(buffer, isLandscape, next) {
			var gmObj = gm(buffer);
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
				queue = "https://sqs.us-east-1.amazonaws.com/435327525078/dev-celery";
			}
			if (queue) {
				var msg_id = uuid.v4();
				var msg_envelope = {
					'content-encoding': 'utf-8',
					'content-type': 'application/json',
					headers: {},
					properties: {
								body_encoding: 'base64',
								correlation_id: msg_id,
								delivery_info: {exchange: null, routing_key: null},
								delivery_tag: null}
				};

				// json_data is the string that will be passed to the celery function
				json_data = JSON.stringify({
								srcKey: srcKey,
								srcBucket: srcBucket,
								thumbnailResults: results});

				// this is the actual celery task body. 'args' will be passed to our task.
				msg_envelope.body = new Buffer(JSON.stringify({
							task: 'core.tasks.finalize_s3_thumbnails',
							args: [ json_data ],
							id: msg_id,
							retries: 0})).toString('base64');

				var sqs = new AWS.SQS({endpoint: "https://sqs.us-east-1.amazonaws.com"});
				sqs.sendMessage({
					QueueUrl: queue,
					MessageBody: new Buffer(JSON.stringify(msg_envelope)).toString('base64'),
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
