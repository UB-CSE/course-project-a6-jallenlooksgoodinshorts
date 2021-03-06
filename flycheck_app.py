from flask import Flask, render_template, url_for, redirect, flash, request, jsonify
from db import updateSentiments, getActivity, getActivityIDs, getAllActivities, joinActivityDB, loginUser, newUser, testConn, createActivity,getUser,userInfo, getInfo, editInfo, likeActivity, getActivityUsers, changeProfPic, getPic,firstNameUser, getcomments, getActivityUsers, writecomment
from forms import LoginForm, RegistrationForm, PostForm, EditForm, ProfileLookupForm, ChangeProfilePicture, CommentForm
from flask_login import LoginManager, login_user, current_user, login_required, UserMixin, logout_user
from flask_bcrypt import Bcrypt
import bcrypt
import sys
import db
import os
import csv
import time
import json
import secrets
import gunicorn
from textblob import TextBlob
from base64 import b64encode

# Runs Bcrypt on server

app = Flask(__name__)
app.config['SECRET_KEY'] = 'you_killed_my_father_prepare_to_die'
port = int(os.environ.get("PORT", 5000))

login_manager = LoginManager(app)


class User(UserMixin):
    def __init__(self, id):
        user = id
        self.id = id

    def get_user(id):
        user = User(id)
        return user


@login_manager.user_loader
def load_user(id):
    return User.get_user(id)


testConn()


bcrypt = Bcrypt(app)


@app.route('/home')
def home():
    return render_template('home.html', title='Home')


@app.route('/browse', methods=['GET', 'POST'])
def browse():

    activityList = getAllActivities()
    activities = []

    for activ in activityList:
        image = b64encode(activ[2]).decode('"utf-8"')
        likes = 0  # Change for likes

        a = {
            'title': activ[0],
            'description': activ[1],
            'image': image,
            'activity_id': activ[4]
        }
        activities.append(a)

    activities.reverse()

    return render_template('browse.html', activities=activities, title='Welcome')


@app.route('/activityfeed', methods=['GET', 'POST'])
@login_required
def activityfeed():

    activityIDs = getActivityIDs(current_user.id)
    activities = []
    print("Current User ID", file=sys.stderr)
    print(current_user.id, file=sys.stderr)

    print("Activity IDs", file=sys.stderr)
    print(activityIDs, file=sys.stderr)
    if activityIDs:
        if activityIDs[0]:
            for ids in activityIDs:
                activ = getActivity(ids[0])

                print("ACTIV", file=sys.stderr)
                print(activ, file=sys.stderr)
                image = b64encode(activ[2]).decode('"utf-8"')
                likes = 0  # Change for likes

                a = {
                    'title': activ[0],
                    'description': activ[1],
                    'image': image,
                    'activity_id': activ[4]
                }
                activities.append(a)

    activities.reverse()

    return render_template('feed.html', activities=activities, title='Activities')


@app.route('/activity/<int:activity_id>', methods=['GET', 'POST'])
def activity(activity_id):
    activ = getActivity(activity_id)
    members = getActivityUsers(activity_id)
    image = b64encode(activ[2]).decode('"utf-8"')
    likes = 0  # Change for likes
    a = {
        'title': activ[0],
        'description': activ[1],
        'image': image,
        'activity_id': activ[4]
    }

    # Setting the sentiments for the activity
    happy               = int(str(activ[5]))
    neutral             = int(str(activ[6]))
    sad                 = int(str(activ[7]))
    totalComments       = int(str(activ[8]))

    dbcomments = getcomments(activity_id)
    comments = []
    if dbcomments:
        if dbcomments[0]:
            for comms in dbcomments:
                fname = firstNameUser(comms[1])
                print("USER ID --------------- Comment", file=sys.stderr)
                print(comms, file=sys.stderr)
                print(fname, file=sys.stderr)
                c = {
                    'username': str(firstNameUser(comms[1]))[2:-3],
                    'body': comms[2]
                }
                comments.append(c)
    y
    form = CommentForm()

    print("-------- PRE FORM ----------", file=sys.stderr)
    if form.validate_on_submit():
        body = form.comment.data
        print("Activity ID --------------- Comment", file=sys.stderr)
        print(current_user.id, file=sys.stderr)

        # Comment Sentiment Analysis
        text = TextBlob(body)
        sentiment = text.polarity

        if (sentiment > 0.4):
            happy += 1
        elif (sentiment < 0) :
            sad += 1
        else:
            neutral +=1

        totalComments += 1

        updateSentiments(activity_id, happy, neutral, sad, totalComments)
        
        
        # End Analysis
        buff = writecomment(current_user.id, activity_id, body)
        return redirect(url_for('activity', activity_id=activity_id))
        


    return render_template('activity.html', activity=a, comments=comments, title='Activity', members=members, form=form)



@app.route('/newpost', methods=['GET', 'POST'])
@login_required
def newpost():
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        description = form.body.data
        image = form.image.data.read()
        activity_id = createActivity(title, description, image)
        print("Activity ID", file=sys.stderr)
        print(activity_id, file=sys.stderr)
        joinActivityDB(current_user.id, activity_id)

        return redirect(url_for('browse'))

    return render_template('newPost.html', title='Post', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        hashedPassword = form.password.data

        if loginUser(email, hashedPassword):
            signedIn = User(email)
            login_user(signedIn)
            return redirect(url_for('browse'))
        else:
            flash(
                'Incorrect login information. Try again or register for an account', 'error')
            return redirect(url_for('login'))

    return render_template('login.html', title='Login', form=form)


@app.route('/register',  methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():

        firstName = form.firstname.data
        lastName = form.lastname.data
        email = form.email.data
        hashedPassword = form.password.data
        username = form.username.data

        newUser(email, hashedPassword, firstName, lastName, username)

        with open('userpass.txt', mode='w') as csvfile:
            writeme = csv.writer(csvfile)
            writeme.writerow([email, hashedPassword])
            csvfile.close()

        flash('account created', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)


@app.route('/joinactivity/<int:activity_id>', methods=['GET', 'POST'])
@login_required
def joinactivity(activity_id):  # joinactivity = server, joinActivity = sql
    joinActivityDB(current_user.id, activity_id)
    return redirect(url_for('activityfeed'))



@app.route('/likeactiivity/<int:activity_id>', methods = ['GET', 'POST'])
@login_required
def likeactivity(activity_id) :
    likeActivity(activity_id)
    return activity(activity_id)




@app.route('/profileinquiry', methods=['GET', 'POST'])
@login_required
def searchprofile():
    form = ProfileLookupForm()

    print("Search Input")
    print(form, file=sys.stderr)

    if form.validate_on_submit():
        returnedInfo = userInfo(form.accproperty.data)

        print("Returned Info Result")
        print(returnedInfo, file=sys.stderr)

        return render_template('profileinquiry.html', title='search', form=form, returnedInfo=returnedInfo)

    return render_template('profileinquiry.html', title='search', form=form)


@ app.route('/otherprofile/<string:user_id>', methods=['GET', 'POST'])
@ login_required
def vprofile(user_id):
    activityIDs = getActivityIDs(user_id)
    returnedInfo = userInfo(user_id)
    activities = []
    print("User ID", file=sys.stderr)
    print(user_id, file=sys.stderr)

    print("Activity IDs", file=sys.stderr)
    print(activityIDs, file=sys.stderr)
    if activityIDs:
        if activityIDs[0]:
            for ids in activityIDs:
                activ = getActivity(ids[0])

                print("ACTIV", file=sys.stderr)
                print(activ, file=sys.stderr)
                image = b64encode(activ[2]).decode('"utf-8"')
                likes = 0  # Change for likes

                a = {
                    'title': activ[0],
                    'description': activ[1],
                    'image': image,
                    'activity_id': activ[4]
                }
                activities.append(a)

    activities.reverse()

    return render_template('otherprofile.html', activities=activities, title='Activities', returnedInfo=returnedInfo)


@ app.route('/profile')
@ login_required
def profile():
    activityIDs = getActivityIDs(current_user.id)
    activities = []
    print("Current User ID", file=sys.stderr)
    print(current_user.id, file=sys.stderr)

    print("Activity IDs", file=sys.stderr)
    print(activityIDs, file=sys.stderr)
    if activityIDs:
        if activityIDs[0]:
            for ids in activityIDs:
                activ = getActivity(ids[0])
                image = b64encode(activ[2]).decode('"utf-8"')
                likes = 0  # Change for likes

                a = {
                    'title': activ[0],
                    'description': activ[1],
                    'image': image,
                    'activity_id': activ[4]
                }
                activities.append(a)

    activities.reverse()

    i = getInfo(current_user.id)

    info = {'about':i[0], 'interests':i[0], 'location':i[0], 'gender':i[0], 'email':i[0]}
    picDb = getPic(current_user.id)
    print(picDb,file=sys.stderr)
    if(picDb != None):
        pic = b64encode(picDb[0]).decode('"utf-8"')

    else:
        pic = None
    return render_template('profile.html', activities=activities, title='Activities', info=info, pic=pic)

@app.route('/editProfile', methods = ['GET', 'POST'])
@login_required
def editinfo():
    form = EditForm()

    if form.validate_on_submit():
        print(current_user.id,file=sys.stderr)
        about = form.about.data
        interests = form.interests.data
        location = form.location.data
        gender = form.gender.data
        i = getInfo(current_user.id)
        if(about == ""):
            about = i[0][0]
        if(interests == ""):
            interests = i[0][1]
        if(location == ""):
            location = i[0][2]
        if(gender == ""):
            gender = i[0][3]
        print(about,file=sys.stderr)
        print(interests, file=sys.stderr)


        editInfo(current_user.id, about, interests, location, gender)
        print(form.errors,file=sys.stderr)
        return redirect(url_for('profile'))
    print(form.errors,file=sys.stderr)
    return render_template('editProfile.html', title = 'Edit', form=form)



@app.route('/changePicture', methods = ['GET', 'POST'])
@login_required
def editProfPic():
    form = ChangeProfilePicture()
    if form.validate_on_submit():
        picture = form.picture.data.read()
        i = changeProfPic(current_user.id, picture)
        print(i,file=sys.stderr)
        return redirect(url_for('profile'))

    return render_template('changePicture.html', title = 'Profile Picture', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=port)

