<h1> ud_fullstack_p4 </h1>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This is my 4th udacity project. I'm Alexey Ustinnikov.
<h2> To run my project:</h2>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Just type `dev_appserver.py .` in project's root to start server(if you are on linux as I do). Google appengine sdk should be installed.
<h2>Description of project:</h2>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I've started with https://github.com/udacity/ud858 and then added my code to files `conference.py` and `models.py`. I've added all api methods that I should add. Don't do any frontend.
<h3>Task 1: Add Sessions to a Conference</h3>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I've created `Session`, `SessionForm` and `SessionForms` in `models.py`. There are `date` and `startTime` fields in `Session`, they are equal to `DateProperty` and `TimeProperty` respectively. `name`, `highlights`, `speaker`, `duration`, `typeOfSession` are `StringField` classes.`date` and `startTime` fields inside `SessionForm` have `StringField` type, because I hasn't founded `DateField` or `TimeField` classes inside `messages`   module, only `DateTimeField`.<br>
<h4>createSession()</h4>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; This function takes `SESS_POST_REQUEST` as request. `SESS_POST_REQUEST` consists of `SessionForm` and parameter `websafeConferenceKey` which is necessary. It will be shown in bold red in api explorer. Only registred user can ran this function, and one can create session only if he is creator of the conference (`organizerUserId` of the conference should be equal to current user_id). Session is created as a child of Conference(parent=conf_key).
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I've also created private function `_copySessionToForm` in order to be able to return `SessionForm` from this function.<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TASK 4 is implemented in the end of this function (setting announcement in memcache for the case when speaker of the session has more then one session to hold in current conference).
<h4>getSessionsBySpeaker()</h4>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Request is `SESS_GET_REQUEST_2`(speaker StringField). Just query all sessions by speaker and return `SessionForms`.
<h4>getConferenceSessionsByType()</h4>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Request is `SESS_GET_REQUEST_3` (`websafeConferenceKey` + `typeOfSession`). Getting conf_key by websafeKey, then query sessions with specific typeOfSession and ancestor equal to conf_key.
<h4>getConferenceSessions()</h4>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Request is `SESS_GET_REQUEST` (only `websafeConferenceKey`). Getting conf_key by websafeKey, then query sessions with  ancestor equal to conf_key.
<h3>Task 2: Add Sessions to User Wishlist</h3>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; I've implemented `addSessionToWishlist()` and `getSessionsInWishlist` api methods. 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`addSessionToWishlist()` takes `SESS_GET_REQUEST_4` (only `SessionKey`) as a request. Making session in `Wishlist` as a child of `Session`.<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`getSessionsInWishlist()` takes VoidMessage as a request. Just quering all `Wishlist`.
<h3>Task 3: Work on indexes and queries</h3>
<h4>Two additional queries</h4>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Please check out `orderSessionsInWishlist()` and `getSessionsByName()` functions.
<h4>Query realted problem</h4>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Check out `getSessionsNotWorkshops()` function. I've tried to solve this problem in code. I think it should work, returning all sessions wish are not workshop and begore 19:00.
<h3>Task 4: Add a Task</h3>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I've added memcache entity in the end of `createSession()` function. Also added `getFeaturedSpeaker()` wich is returning name of the speaker from the memcache. Memcache key is `ABOUT_SPEAKER` definied at the top of `confrerenc.py`.



