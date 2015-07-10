#-*- coding: utf-8 -*-

from core.shared.const.choice_enum import ChoiceEnum


class NotificationTypes(ChoiceEnum):
    EVENT_INVITE = 1
    EVENT_UPDATE = 3
    EVENTGUEST_RSVP = 2
    ALBUMFILE_UPLOAD = 4
    ACCOUNT_EMAIL_VALIDATE = 5

#EOF
