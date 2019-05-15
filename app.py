import os
from flask import Flask, render_template, session, jsonify, redirect, url_for
import json
from datetime import datetime
from model import User, Product, Dish, HistoryEntry, diet_labels
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'
SECRET_KEY = os.urandom(24)

app = Flask(__name__)
app.secret_key = SECRET_KEY

def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}

with open('response.json') as res_file:
    response = json.load(res_file)

results = [Dish(hit['recipe']) for hit in response['hits']]

mock_user = User(1, 'Test', 'User')
mock_products = [Product('Chicken', 2, 'kg'), Product('Butter', 200, 'g')]
mock_user.products = mock_products


@app.route('/')
def index():
    return render_template('search_layout.html')


@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri='http://127.0.0.1:5000/profiles/1')

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    session['state'] = state
    return redirect(authorization_url)


@app.route('/profiles/<profile>')
def profile(profile):
    credentials = google.oauth2.credentials.Credentials(
        **session['credentials'])

    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    files = drive.files().list().execute()
    session['credentials'] = credentials_to_dict(credentials)
    return render_template('profile.html', profile=mock_user)


@app.route('/profiles/<profile_id>/history')
def profile_history(profile_id):
    return render_template('history.html', profile=mock_user)


@app.route('/profiles/<profile_id>/favourites')
def profile_favourites(profile_id):
    return render_template('favourites.html', profile=mock_user)


@app.route('/profiles/<profile_id>/products', methods=['GET', 'POST'])
def profile_products(profile_id):
    if request.method == 'POST':
        mock_user.products.append(
            Product(request.form.get('name'), request.form.get('quantity'), request.form.get('unit')))
    return render_template('products.html', profile=mock_user)


@app.route('/recipes', methods=['GET', 'POST'])
def recipe_results():
    query = request.form['query']
    if query in mock_user.history:
        mock_user.history.remove(query)
    mock_user.history.append(HistoryEntry(query, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    return render_template('recipes.html', labels=diet_labels, recipes=results)


@app.route('/recipes/<recipe_id>', methods=['GET', 'POST'])
def recipe_details(recipe_id):
    # TODO if the recipe was chosen from the favourites -> get it from db, if from search results -> get it from results
    for res in results:
        if res.id == recipe_id:
            recipe = res
    if request.method == 'POST':
        if recipe not in mock_user.favourites:
            mock_user.favourites.append(recipe)
    return render_template('recipe.html', labels=diet_labels, recipe=recipe)


if __name__ == '__main__':
    app.run()
