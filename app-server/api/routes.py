from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt as jwt
from flask import request
from flask_restx import Api, fields, Resource

from ai_models.emotion_recognition_helpers import EmotionRecognition
from api.config import Config
from api.models import User, JWTTokenBlocklist, db, JournalEntry, PatientTherapistRelation

emotion_recognition = EmotionRecognition()

rest_api = Api(version='1.0', title='TherapEase REST API')

login_model = rest_api.model('LoginModel', {
    'email': fields.String(required=True, min_length=4, max_length=64),
    'password': fields.String(required=True, min_length=4, max_length=64)
})

register_model = rest_api.model('RegisterModel', {
    'username': fields.String(required=True, min_length=4, max_length=64),
    'email': fields.String(required=True, min_length=4, max_length=64),
    'password': fields.String(required=True, min_length=4, max_length=64),
    'type_of_account': fields.String(required=True, min_length=4, max_length=64),
    'first_name': fields.String(required=True, min_length=4, max_length=64),
    'last_name': fields.String(required=True, min_length=4, max_length=64),
    'date_of_birth': fields.Date(required=True),
    'gender': fields.String(required=True, min_length=4, max_length=64),
    'country': fields.String(required=True, min_length=4, max_length=64),
    'city': fields.String(required=True, min_length=4, max_length=64),
    'therapist_speciality': fields.String(required=False, min_length=0, max_length=64),
    'therapist_location': fields.String(required=False, min_length=0, max_length=64)
})

update_user_model = rest_api.model('UpdateUserModel', {
    'username': fields.String(required=True, min_length=4, max_length=64),
    'first_name': fields.String(required=True, min_length=4, max_length=64),
    'last_name': fields.String(required=True, min_length=4, max_length=64),
    'date_of_birth': fields.Date(required=True),
    'gender': fields.String(required=True, min_length=4, max_length=64),
    'country': fields.String(required=True, min_length=4, max_length=64),
    'city': fields.String(required=True, min_length=4, max_length=64),
    'therapist_speciality': fields.String(required=False, min_length=0, max_length=64),
    'therapist_location': fields.String(required=False, min_length=0, max_length=64)
})

post_journal_model = rest_api.model('JournalModel', {
    'entry_title': fields.String(required=True, min_length=4, max_length=64),
    'entry_text': fields.String(required=True, min_length=4)
})

update_journal_model = rest_api.model('UpdateJournalModel', {
    '_id': fields.Integer(required=True),
    'entry_title': fields.String(required=False, min_length=4, max_length=64),
    'entry_text': fields.String(required=False, min_length=4)
})


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]
        if not token:
            return {'success': False, 'msg': 'Valid JWT Token is missing'}, 400
        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user = User.find_by_email(data['email'])
            if not current_user:
                return {'success': False, 'msg': 'Invalid user'}, 400
            token_expired = db.session.query(JWTTokenBlocklist.id).filter_by(jwt_token=token).scalar()
            if token_expired is not None:
                return {"success": False, "msg": "Token revoked."}, 400
            if not current_user.check_jwt_auth_active():
                return {'success': False, 'msg': 'JWT Token authentication is not active for this user'}, 400
        except Exception as e:
            print(e)
            return {"success": False, "msg": "Invalid JWT Token"}, 400
        return f(current_user, *args, **kwargs)
    return decorator


@rest_api.route('/api/users/register')
class Register(Resource):
    @rest_api.expect(register_model, validate=True)
    def post(self):
        request_data = request.get_json()
        _username = request_data.get('username')
        _email = request_data.get('email')
        _password = request_data.get('password')
        _type_of_account = request_data.get('type_of_account')
        _first_name = request_data.get('first_name')
        _last_name = request_data.get('last_name')
        _date_of_birth = request_data.get('date_of_birth')
        _gender = request_data.get('gender')
        _country = request_data.get('country')
        _city = request_data.get('city')
        _therapist_speciality = None
        _therapist_location = None
        if _type_of_account == 'therapist':
            _therapist_speciality = request_data.get('therapist_speciality')
            _therapist_location = request_data.get('therapist_location')
        if User.find_by_email(_email):
            return {'success': False, 'msg': 'User with this email already exists'}, 400
        if User.find_by_username(_username):
            return {'success': False, 'msg': 'User with this username already exists'}, 400

        new_user = User(username=_username,
                        email=_email,
                        type_of_account=_type_of_account,
                        first_name=_first_name,
                        last_name=_last_name,
                        date_of_birth=_date_of_birth,
                        gender=_gender,
                        country=_country,
                        city=_city,
                        therapist_speciality=_therapist_speciality,
                        therapist_location=_therapist_location)
        new_user.set_password(_password)
        new_user.save()

        return {'success': True, 'msg': 'User created successfully'}, 201


@rest_api.route('/api/users/login')
class Login(Resource):
    @rest_api.expect(login_model, validate=True)
    def post(self):
        request_data = request.get_json()
        _email = request_data.get('email')
        _password = request_data.get('password')
        user_exists = User.find_by_email(_email)
        if not user_exists:
            return {'success': False, 'msg': 'User does not exist'}, 400
        if not user_exists.check_password(_password):
            return {'success': False, 'msg': 'Invalid password'}, 400

        token = jwt.encode({'email': _email, 'exp': datetime.utcnow() + Config.JWT_ACCESS_TOKEN_EXPIRES}, Config.SECRET_KEY)
        user_exists.set_jwt_auth_active(True)
        user_exists.save()
        return {'success': True, 'user': user_exists.to_json(), 'token': token}, 200


@rest_api.route('/api/users/logout')
class Logout(Resource):
    @token_required
    def post(self, current_user):
        token = request.headers['Authorization']
        token_blocklist = JWTTokenBlocklist(jwt_token=token, created_at=datetime.now(timezone.utc))
        token_blocklist.save()
        self.set_jwt_auth_active(False)
        self.save()
        return {'success': True, 'msg': 'User logged out successfully'}, 200


@rest_api.route('/api/patients/journals')
class Journal(Resource):
    @token_required
    def get(self, current_user):
        journals = JournalEntry.find_by_user_id(self.id)
        return {'success': True, 'journals': [journal.to_json() for journal in journals]}, 200

    @token_required
    @rest_api.expect(post_journal_model, validate=True)
    def post(self, current_user):
        request_data = request.get_json()
        _title = request_data.get('entry_title')
        _content = request_data.get('entry_text')
        prediction = emotion_recognition.predict(_content)
        new_journal = JournalEntry(entry_title=_title, entry_text=_content, user_id=self.id, entry_date=datetime.now(timezone.utc), predicted_emotion=prediction)
        new_journal.save()
        return {'success': True, 'msg': 'Journal created successfully'}, 201


@rest_api.route('/api/patients/journal/<int:id>')
class JournalEntryRoute(Resource):
    @token_required
    def get(self, current_user, id):
        journal = JournalEntry.find_by_id(id)
        if not journal:
            return {'success': False, 'msg': 'Journal does not exist'}, 400
        if journal.user_id != self.id:
            return {'success': False, 'msg': 'Journal does not belong to this user'}, 400
        return {'success': True, 'journal': journal.to_json()}, 200

    @token_required
    @rest_api.expect(update_journal_model, validate=True)
    def put(self, current_user, id):
        request_data = request.get_json()
        _id = request_data.get('_id')
        _title = request_data.get('entry_title')
        _content = request_data.get('entry_text')
        journal = JournalEntry.find_by_id(_id)
        if not journal:
            return {'success': False, 'msg': 'Journal does not exist'}, 400
        journal.entry_title = _title
        journal.entry_text = _content
        journal.predicted_emotion = emotion_recognition.predict(_content)
        journal.save()
        return {'success': True, 'msg': 'Journal updated successfully'}, 200

    @token_required
    def delete(self, current_user, id):
        print(id)
        journal = JournalEntry.find_by_id(id)
        if not journal:
            return {'success': False, 'msg': 'Journal does not exist'}, 400
        journal.delete()
        return {'success': True, 'msg': 'Journal deleted successfully'}, 200


@rest_api.route('/api/therapists')
class Therapist(Resource):
    @token_required
    def get(self, current_user):
        # get all the patients of the therapist
        patient_therapist_relations = PatientTherapistRelation.find_by_therapist_id(self.id)
        patients = []
        for relation in patient_therapist_relations:
            patient = User.find_by_id(relation.patient_id)
            patients.append(patient)
        return {'success': True, 'patients': [patient.get_all_details() for patient in patients]}, 200

    @token_required
    def post(self, current_user):
        # add a patient to the therapist
        request_data = request.get_json()
        patient_email = request_data.get('email')
        if not User.find_by_email(patient_email):
            return {'success': False, 'msg': 'Patient does not exist'}, 400
        # check if the user is already a patient of a therapist
        patient = User.find_by_email(patient_email)
        patient_therapist_relation = PatientTherapistRelation.find_by_patient_id(patient.id)
        if patient_therapist_relation:
            return {'success': False, 'msg': 'Patient already has a therapist'}, 400
        # check if the id of the patient is a therapist
        if patient.type_of_account == 'therapist':
            return {'success': False, 'msg': 'Patient is a therapist'}, 400

        # add the patient to the therapist
        patient_therapist_relation = PatientTherapistRelation(patient_id=patient.id, therapist_id=self.id)
        patient_therapist_relation.save()
        return {'success': True, 'msg': 'Patient added successfully'}, 201


@rest_api.route('/api/therapists/patient/<int:patient_id>')
class TherapistPatient(Resource):
    @token_required
    def get(self, current_user, patient_id):
        # get the patient by the id
        patient = User.find_by_id(patient_id)
        if not patient:
            return {'success': False, 'msg': 'Patient does not exist'}, 400
        if patient.type_of_account != 'patient':
            return {'success': False, 'msg': 'User is not a patient'}, 400
        # check if the requested patient is a patient of the therapist
        patient_therapist_relation = PatientTherapistRelation.find_by_patient_id(patient_id)
        if not patient_therapist_relation:
            return {'success': False, 'msg': 'Patient is not a patient of the therapist'}, 400
        # compute list of all emotions of the journals of the patient, with the corresponding dates
        journals = JournalEntry.find_by_user_id(patient_id)
        emotions = []
        for journal in journals:
            emotions.append({'emotion': journal.predicted_emotion, 'date': str(journal.entry_date)})
        return {'success': True, 'patient': patient.get_all_details(), 'emotions': emotions}, 200


    @token_required
    def delete(self, current_user, patient_id):
        # check if the patient is a patient of the therapist
        patient_therapist_relation = PatientTherapistRelation.find_by_patient_id(patient_id)[0]
        if not patient_therapist_relation:
            return {'success': False, 'msg': 'Patient is not a patient of the therapist'}, 400
        # delete the patient from the therapist
        patient_therapist_relation.delete()
        return {'success': True, 'msg': 'Patient deleted successfully'}, 200


@rest_api.route('/api/users/account')
class Users(Resource):
    @token_required
    def get(self, current_user):
        return {'success': True, 'user': self.get_all_details()}, 200

    @token_required
    @rest_api.expect(update_user_model, validate=True)
    def put(self, current_user):
        request_data = request.get_json()
        print(request_data)
        _username = request_data.get('username')
        _first_name = request_data.get('first_name')
        _last_name = request_data.get('last_name')
        _gender = request_data.get('gender')
        _date_of_birth = request_data.get('date_of_birth')
        _country = request_data.get('country')
        _city = request_data.get('city')
        _therapist_speciality = None
        _therapist_location = None
        if self.type_of_account == 'therapist':
            _therapist_speciality = request_data.get('therapist_speciality')
            _therapist_location = request_data.get('therapist_location')
        user = User.find_by_id(self.id)
        if not user:
            return {'success': False, 'msg': 'User does not exist'}, 400
        user.first_name = _first_name
        user.last_name = _last_name
        user.username = _username
        user.gender = _gender
        user.date_of_birth = _date_of_birth
        user.country = _country
        user.city = _city
        if self.type_of_account == 'therapist':
            user.therapist_speciality = _therapist_speciality
            user.therapist_location = _therapist_location
        user.save()
        return {'success': True, 'msg': 'User updated successfully'}, 200


@rest_api.route('/api/users/account/password')
class UsersPassword(Resource):
    @token_required
    def put(self, current_user):
        request_data = request.get_json()
        _password = request_data.get('password')
        _new_password = request_data.get('new_password')
        user = User.find_by_id(self.id)
        if not user:
            return {'success': False, 'msg': 'User does not exist'}, 400
        if not user.check_password(_password):
            return {'success': False, 'msg': 'Wrong password'}, 400
        user.set_password(_new_password)
        user.save()
        return {'success': True, 'msg': 'Password updated successfully'}, 200
