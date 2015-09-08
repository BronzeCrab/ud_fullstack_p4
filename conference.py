#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'


from datetime import datetime
from datetime import date
from datetime import time

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import StringMessage
from models import BooleanMessage
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import TeeShirtSize
from models import Session
from models import SessionForm
from models import SessionForms
from models import Wishlist

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId

import re

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
ANNOUNCEMENT_TPL = ('Last chance to attend! The following conferences '
                    'are nearly sold out: %s')
ABOUT_SPEAKER = "Announcement about speaker"
ANNOUNCEMENT_SPEAKER = ('There is more then one session by speaker '
                        '%s in sessions %s')
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": ["Default", "Topic"],
}

OPERATORS = {
    'EQ': '=',
    'GT': '>',
    'GTEQ': '>=',
            'LT': '<',
            'LTEQ': '<=',
            'NE': '!='
}

FIELDS = {
    'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
}


CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)
# Container for getConferenceSessions()
SESS_GET_REQUEST = endpoints.ResourceContainer(
    websafeConferenceKey=messages.StringField(1),
)
# Container for createSession()
SESS_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)
# Container for getSessionsBySpeaker()
SESS_GET_REQUEST_2 = endpoints.ResourceContainer(
    speaker=messages.StringField(1),
)
# Container for getConferenceSessionsByType()
SESS_GET_REQUEST_3 = endpoints.ResourceContainer(
    websafeConferenceKey=messages.StringField(1),
    typeOfSession=messages.StringField(2),
)
# Container for addSessionToWishlist()
SESS_GET_REQUEST_4 = endpoints.ResourceContainer(
    SessionKey=messages.StringField(1),
)
# Container for getSessionsByName()
SESS_GET_REQUEST_5 = endpoints.ResourceContainer(
    name=messages.StringField(1),
)
# === Dummy Session for testing ===
# # create dummy session for testing purposes
# session = Session(name = "Testing",
#                   highlights = "About testing",
#                   speaker = "Alex",
#                   duration = "4 hours",
#                   typeOfSession = "lection",
#                   date = datetime(2015, 9, 3),
#                   startTime = datetime(2015,9,3,21,00))
# # put dummy session into db
# session_key = session.put()
# === Dummy Session for testing ===

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(
    name='conference',
    version='v1',
    audiences=[ANDROID_AUDIENCE],
    allowed_client_ids=[
        WEB_CLIENT_ID,
        API_EXPLORER_CLIENT_ID,
        ANDROID_CLIENT_ID,
        IOS_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    def _createConferenceObject(self, request):
        """Create or update Conference object, returning
           ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        print " got current user"
        print user
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)
        print " got user id"
        print user_id
        if not request.name:
            raise endpoints.BadRequestException(
                "Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        print " vot cho v reauest"
        print request
        print "scopirovali v data, 4o v data"
        print data
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound
        # Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])
        print "postavili po defoltu"
        print data
        print "data['startDate'][:10]"
        # convert dates from strings to Date objects; set month based on
        # start_date
        if data['startDate']:
            print data['startDate'][:10]
            data['startDate'] = datetime.strptime(
                data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(
                data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        print "p_key = ndb.Key(Profile, user_id) 4e v p_key"
        print p_key
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]

        print "Conference.allocate_ids(size=1, parent=p_key)"
        print Conference.allocate_ids(size=1, parent=p_key)

        c_key = ndb.Key(Conference, c_id, parent=p_key)

        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
                              'conferenceInfo': repr(request)},
                      url='/tasks/send_confirmation_email'
                      )
        return request

    @ndb.transactional()
    def _updateConferenceObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
                      http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(CONF_POST_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='PUT', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='getConferencesCreated',
                      http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[
                self._copyConferenceToForm(
                    conf,
                    getattr(
                        prof,
                        'displayName')) for conf in confs])

    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(
                filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q

    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name)
                     for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException(
                    "Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is
                # performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException(
                        "Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='queryConferences',
                      http_method='POST',
                      name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId))
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
            items=[
                self._copyConferenceToForm(
                    conf, names[
                        conf.organizerUserId]) for conf in conferences])


# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(
                        pf, field.name, getattr(
                            TeeShirtSize, getattr(
                                prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key=p_key,
                displayName=user.nickname(),
                mainEmail=user.email(),
                teeShirtSize=str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        # if field == 'teeShirtSize':
                        #    setattr(prof, field, str(val).upper())
                        # else:
                        #    setattr(prof, field, val)
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)

    @endpoints.method(message_types.VoidMessage, ProfileForm,
                      path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @staticmethod
    def _setSpeakerAnnouncement(speaker, sessions):
        """Create Announcement about speaker and
        assign to memcache.
        """
        # announcement = ANNOUNCEMENT_SPEAKER % (speaker, speaker)
        # converting string back to dict
        sessions = eval(sessions)
        announcement = ANNOUNCEMENT_SPEAKER % (speaker, ', '.join(
            sessions[i] for i in sessions))
        memcache.set(ABOUT_SPEAKER, announcement)

        return announcement

    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='conference/announcement/get',
                      http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        return StringMessage(data=memcache.get(
            MEMCACHE_ANNOUNCEMENTS_KEY) or "")


# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser()  # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conferences/attending',
                      http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser()  # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck)
                     for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId)
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[
                self._copyConferenceToForm(
                    conf, names[
                        conf.organizerUserId]) for conf in conferences])

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='filterPlayground',
                      http_method='GET', name='filterPlayground')
    def filterPlayground(self, request):
        """Filter Playground"""
        q = Conference.query()
        # field = "city"
        # operator = "="
        # value = "London"
        # f = ndb.query.FilterNode(field, operator, value)
        # q = q.filter(f)
        q = q.filter(Conference.city == "London")
        q = q.filter(Conference.topics == "Medical Innovations")
        q = q.filter(Conference.month == 6)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )

    def _copySessionToForm(self, session):
        """Copy relevant fields from Session to SessionForm."""
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(session, field.name):
                # convert date to date string;
                # covert time to string, just copy others
                if field.name.endswith(
                        'date') or field.name.endswith('startTime'):
                    setattr(sf, field.name, str(getattr(session, field.name)))
                else:
                    setattr(sf, field.name, getattr(session, field.name))
        sf.check_initialized()
        return sf

    @endpoints.method(SESS_POST_REQUEST, SessionForm,
                      path='sessions/{websafeConferenceKey}',
                      http_method='POST', name='createSession')
    def createSession(self, request):
        """Create new session in given conference."""
        # user should be authorized:
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)
        # checking if name is not null:
        if not request.name:
            raise endpoints.BadRequestException(
                "Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict:
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        # del field sessionKey cause it's not in model Session
        # sessionKey is only necessary when creating Wishlist
        del data['sessionKey']
        # getting Conference to check if current user is organizer:
        try:
            conference = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        except:
            raise endpoints.BadRequestException(
                "No such conference, check websafeKey")

        # getting id of organizer of current conference:
        organizer_id = getattr(conference, 'organizerUserId')

        # only onrganizer can create session in conference:
        if organizer_id != user_id:
            raise endpoints.ForbiddenException(
                "Denied, you can't create session")

        # convert date from string to Date object
        if data['date']:
            data['date'] = datetime.strptime(
                data['date'][:10], "%Y-%m-%d").date()

        # convert time from string to Time object
        if data['startTime']:
            data['startTime'] = datetime.strptime(
                data['startTime'][:10], "%H-%M").time()

        # getting Conference key:
        conf_key = getattr(conference, 'key')
        if not conf_key:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeKey)

        # allocating id for session:
        sess_id = Session.allocate_ids(size=1, parent=conf_key)[0]

        # making key for session, parent is conference:
        sess_key = ndb.Key(Session, sess_id, parent=conf_key)

        # adding session key to dict:
        data['key'] = sess_key

        del data['websafeConferenceKey']
        # putting data to the store:
        Session(**data).put()

        # TASK 4
        # checking if there is more then one session
        # by this speaker at the conference.

        # get conference by key:
        conf = conf_key.get()
        # get all Sessions in the conference:
        sessions = Session.query(
            ancestor=conf_key).filter(
            Session.speaker == data['speaker'])
        sessions_count = sessions.count()
        # ==== old variant ====
        # sessions = Session.query(ancestor=conf_key).fetch()
        # count_speaker = 0
        # # iterating through all sessions:
        # for session in sessions:
        #     if session.speaker and session.speaker == data['speaker']:
        #         count_speaker += 1
        # ==== old variant ====
        sessions_names = {}
        for ind, session in enumerate(sessions.fetch()):
            sessions_names[ind] = session.name
        print "ololo"
        print sessions_names
        if sessions_count > 1:
            taskqueue.add(
                params={'speaker': data['speaker'],
                        'sessions': repr(sessions_names)},
                url='/tasks/set_featured_speaker')
            # taskqueue.add(
            #     params={
            #         'speaker': data['speaker'],
            #         'sessions': sessions_names},
            #     url='/tasks/set_featured_speaker')

            # ==== old variant ====
            # add new memcache entity:
            # format announcement and set it in memcache
            # announcement = ANNOUNCEMENT_SPEAKER % (data['speaker'], ', '.join(
            #     session.name for session in sessions if session.speaker == data['speaker']))
            # memcache.set(ABOUT_SPEAKER, announcement)
            # ==== old variant ====

        return self._copySessionToForm(request)

    @endpoints.method(SESS_GET_REQUEST, SessionForms,
                      path='conferences/{websafeConferenceKey}/sessions',
                      http_method='GET', name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Get all sessions from given conference"""
        # get conference key:
        conf_key = ndb.Key(urlsafe=request.websafeConferenceKey)
        # get all sessions from conference (using ancestor for strong
        # consistensy:
        sessions = Session.query(ancestor=conf_key).fetch()
        return SessionForms(
            sessions=[
                self._copySessionToForm(session) for session in sessions])

    @endpoints.method(SESS_GET_REQUEST_5, SessionForms,
                      path='sessions/name/{name}',
                      http_method='GET', name='getSessionsByName')
    def getSessionsByName(self, request):
        """Get all sessions by name of the session from all conferences"""
        # getting all sessions with current speaker:
        sessions = Session.query(Session.name == request.name).fetch()
        return SessionForms(
            sessions=[
                self._copySessionToForm(session) for session in sessions])

    @endpoints.method(SESS_GET_REQUEST_2, SessionForms,
                      path='sessions/speaker/{speaker}',
                      http_method='GET', name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Get all sessions by speaker from all conferences"""
        # getting all sessions with current speaker:
        sessions = Session.query(Session.speaker == request.speaker).fetch()
        return SessionForms(
            sessions=[
                self._copySessionToForm(session) for session in sessions])

    @endpoints.method(
        SESS_GET_REQUEST_3,
        SessionForms,
        path='conferences/{websafeConferenceKey}/sessions/{typeOfSession}',
        http_method='GET',
        name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Get sessions with certain typeOfSession from given conf"""
        # get conference key:
        conf_key = ndb.Key(urlsafe=request.websafeConferenceKey)
        # query for sessions with specific typeOfSession
        sessions = Session.query(
            Session.typeOfSession == request.typeOfSession,
            ancestor=conf_key).fetch()
        return SessionForms(
            sessions=[
                self._copySessionToForm(session) for session in sessions])

    @endpoints.method(
        SESS_GET_REQUEST_4,
        SessionForm,
        path='wishlist/{SessionKey}',
        http_method='POST',
        name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        """Copy Session to Wishlist"""
        # first of all there is a need to check if this session is
        # already in wishlist:
        sessInWishlist = Wishlist.query(
            Wishlist.sessionKey == request.SessionKey).count()
        if sessInWishlist != 0:
            raise endpoints.ForbiddenException(
                "Denied, you can't create one session in wishlist twice")
        else:
            # get session and key:
            session_key = ndb.Key(urlsafe=request.SessionKey)
            session = session_key.get()
            # allocating id for session in wishlist:
            sess_wish_id = Wishlist.allocate_ids(size=1, parent=session.key)[0]
            # making key for session in wish, parent is just session:
            sess_wish_key = ndb.Key(Wishlist, sess_wish_id, parent=session.key)
            # in order not to deal with converting
            # dateandtime objects to string setting new
            # variables:
            date, startTime = None, None
            if session.date is not None:
                date = session.date
                del session.date
            if session.startTime is not None:
                startTime = session.startTime
                del session.startTime
            # making form from session to make dict and then give
            # that dict into Wishlist:
            session_form = self._copySessionToForm(session)
            # making dict with all data:
            data = {field.name: getattr(session_form, field.name)
                    for field in session_form.all_fields()}
            data['date'] = date
            data['startTime'] = startTime
            data['sessionKey'] = session_key.urlsafe()
            # adding session_wish key to dict:
            data['key'] = sess_wish_key
            Wishlist(**data).put()
        return session_form

    @endpoints.method(message_types.VoidMessage, SessionForms,
                      path='wishlist',
                      http_method='GET', name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Get all sessions from Wishlist"""
        sessions = Wishlist.query()
        return SessionForms(
            sessions=[
                self._copySessionToForm(session) for session in sessions])

    @endpoints.method(message_types.VoidMessage, SessionForms,
                      path='wishlist/sort=starttime',
                      http_method='GET', name='orderSessionsInWishlist')
    def orderSessionsInWishlist(self, request):
        """Filter Wishlist first by startTime"""
        # get sessions from wishlist
        wish_sessions = Wishlist.query()
        # first order by time by startTime:
        wish_sessions = wish_sessions.order(Wishlist.startTime)
        return SessionForms(
            sessions=[
                self._copySessionToForm(session) for session in wish_sessions])

    @endpoints.method(message_types.VoidMessage, SessionForms,
                      path='wishlist/type=notworkshop&sort=time',
                      http_method='GET', name='getSessionsNotWorkshops')
    def getSessionsNotWorkshops(self, request):
        """Get all sessions in wishlist not workshops and before 19-00"""
        # getting all sessions not type of workshop
        s = Session.query()
        s = s.filter(Wishlist.typeOfSession != 'workshop')
        # now filter all data by time:
        sessions = [self._copySessionToForm(session) for session in s]
        sessions_filteredTime = [self._copySessionToForm(
            session) for session in sessions if session.startTime[0:2] <= '19']
        return SessionForms(sessions=[self._copySessionToForm(
            session) for session in sessions_filteredTime])

    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='speaker',
                      http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Returns speaker name with more then 1 session"""
        # getting string from memcache:
        ann = memcache.get(ABOUT_SPEAKER)
        # using reg exp to find speaker name in string:
        try: 
            matchObj = re.search(r'speaker (.*?) in', ann)
        except:
            raise endpoints.BadRequestException(
                "Not find anything in memcache")

        return StringMessage(data=matchObj.group(1))

api = endpoints.api_server([ConferenceApi])  # register API
