"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, Message, User, Like

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app


app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageBaseViewTestCase(TestCase):
    def setUp(self):
        Like.query.delete()
        Message.query.delete()
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()

        m1 = Message(text="m1-text", user_id=u1.id)

        db.session.add_all([m1])
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id

        self.client = app.test_client()


class MessageAddViewTestCase(MessageBaseViewTestCase):
    def test_add_message(self):
        """test that a logged in user can create a new message and it's in the database"""
        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            resp = c.post("/messages/new",
                          data={"text": "Hello"}, follow_redirects=True)
            html = resp.get_data(as_text=True)

            msg = Message.query.filter_by(text="Hello").one()

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Hello", html)
            self.assertIn("u1", html)
            self.assertIsNotNone(msg)

    def test_add_message_logout_user(self):
        """ test logged out user can't add message"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            c.post("/logout", follow_redirects=True)

            resp = c.post("/messages/new",
                          data={"text": "Hello"}, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)




#TODO: refactor classes for test cases

    def test_show_message(self):
        """test that a message shows"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get(f"/messages/{self.m1_id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("m1-text", html)

    def test_delete_message(self):
        """test that user can delete a message and it doesn't show up on user's page"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(
                f'/messages/{self.m1_id}/delete', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("m1-text", html)
            msg = Message.query.get(self.m1_id)
            self.assertIsNone(msg)

    def test_delete_message_logout_user(self):
        """ test logged out user can't delete message"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            c.post("/logout", follow_redirects=True)

            resp = c.post(
                f"/messages/{self.m1_id}/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_like_message(self):
        """test that user can like a message"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post(f"/like/{self.m1_id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Unlike", html)

    def test_unlike_message(self):
        """test that user can unlike message"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            u2 = User.query.get(self.u2_id)
            m1 = Message.query.get(self.m1_id)

            u2.liked_messages.append(m1)
            db.session.commit()

            resp = c.post(f"/unlike/{self.m1_id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("Unlike", html)

    def test_show_liked_messages(self):
        """ test showing liked messages from user"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            u2 = User.query.get(self.u2_id)
            m1 = Message.query.get(self.m1_id)

            u2.liked_messages.append(m1)
            db.session.commit()

            resp = c.get(f"/users/{self.u2_id}/likes")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("m1-text", html)


# TODO: NOT POSSIBLE HERE BUT STH TO THINK ABOUT:
# When you???re logged in, are you prohibiting from adding a message as another user?
# When you???re logged in, are you prohibiting from deleting a message as another user?
