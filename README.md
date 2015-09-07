<h1> ud_fullstack_p4 </h1>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This is my 4th udacity project. I'm Alexey Ustinnikov.
<h2> To run my project:</h2>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Just type `dev_appserver.py .` in project's root to start server(if you are on linux as I do). Google appengine sdk should be installed.
<h2>Description of project:</h2>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I've started with https://github.com/udacity/ud858 and then added my code to files `conference.py` and `models.py`. I've added all api methods that I should add. Don't do any frontend.
<h3>Task 1: Add Sessions to a Conference</h3>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I've created `Session`, `SessionForm` and `SessionForms` in `models.py`. There are `date` and `startTime` fields in `Session`, they are equal to `DateProperty` and `TimeProperty` respectively. `name`, `highlights`, `speaker`, `duration`, `typeOfSession` are `StringField` classes.`date` and `startTime` fields inside `SessionForm` have `StringField` type, because I hasn't founded `DateField` or `TimeField` classes inside `messages`   module, only `DateTimeField`.<br>
<h4>createSession()/h4>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I've also created private function _
<h4>getSessionsBySpeaker()</h4>
<h4>getConferenceSessionsByType()</h4>
<h4>getConferenceSessions()</h4> 
<h3>Task 2: Add Sessions to User Wishlist</h3>
<h3>Task 3: Work on indexes and queries</h3>
<h3>Task 4: Add a Task</h3>


necessary

respectively
