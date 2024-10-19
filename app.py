from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = '2a38fdd7dea359fbd744fe41'  # Replace with a secure key in production

# Database connection details
db = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="foodwaste"
)

# Edamam API credentials
app_id = '76f17ad0'  # Replace with your Edamam App ID
app_key = '0250325b6e1ecbeaa7f31ce24da04370'  # Replace with your Edamam App Key

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Route for Homepage (home.html)
@app.route('/')
def home_page():
    return render_template('home.html')


# Route for Homepage (contact.html)
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Route for Login Page (HTML)
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials in the database
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM account WHERE username = %s", (username,))
            user = cursor.fetchone()

        logging.debug(f"Username: {username}, User found: {user}")  # Log the username and user fetch result

        if user:
            if check_password_hash(user[2], password):  # user[2] is the hashed password column
                session['user_id'] = user[0]  # Store user ID in session
                session['username'] = user[1]  # Store username in session
                return redirect(url_for('home_page', status='success'))  # Redirect with success status
            else:
                return redirect(url_for('login_page', status='invalid'))  # Redirect with invalid password status
        else:
            return redirect(url_for('login_page', status='not_registered'))  # Redirect with username not found status

    return render_template('login.html')

# Check if username already exists
@app.route('/check-username')
def check_username():
    username = request.args.get('username')
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM account WHERE username = %s", (username,))
        user = cursor.fetchone()
    exists = user is not None
    return jsonify({'exists': exists})

# Route for Register Page (HTML)
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Insert new user into the database
        with db.cursor() as cursor:
            try:
                cursor.execute("INSERT INTO account (username, password) VALUES (%s, %s)", (username, hashed_password))
                db.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login_page'))
            except pymysql.IntegrityError:
                flash('Username already exists. Please choose a different username.', 'danger')

    return render_template('register.html')

# Route for Storage Page (HTML)
@app.route('/storage')
def ingredients_page():
    return render_template('storage.html')

# API to fetch ingredients from the database
@app.route('/api/storage', methods=['GET'])
def get_ingredients():
    user_id = session.get('user_id', 1)  # Adjust user_id logic as needed; default to 1 if not logged in
    with db.cursor() as cursor:
        query = "SELECT foodname, quantity, expdate FROM storage WHERE userid = %s"
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()

    # Format the result as a list of dictionaries (JSON)
    ingredients = []
    for row in rows:
        ingredient = {
            'food_name': row[0],
            'quantity': row[1],
            'expiration_date': row[2].strftime('%Y-%m-%d')  # Format date to YYYY-MM-DD
        }
        ingredients.append(ingredient)

    # Return the data as JSON
    return jsonify(ingredients)

# Route for the Nutrition/Recipe Recommender Page (HTML)
@app.route('/nutrition')
def nutrition_page():
    return render_template('nutrition.html')

# Function to search for recipes using Edamam API
def search_recipes(query, app_id, app_key, calories):
    url = 'https://api.edamam.com/search'
    
    # Set calorie filter based on the user's selection
    calorie_range = None
    if calories == '1':
        calorie_range = '0-500'
    elif calories == '2':
        calorie_range = '0-1000'
    elif calories == '3':
        calorie_range = '2000+'  # More than 2000 kcal
    
    # API parameters
    params = {
        'q': query,
        'app_id': app_id,
        'app_key': app_key,
        'from': 0,
        'to': 10
    }
    
    # Add calorie filter if applicable
    if calorie_range:
        params['calories'] = calorie_range
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for bad responses
    except requests.RequestException as e:
        logging.error(f"Error fetching recipes: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

    data = response.json()
    
    recipes = []
    for recipe in data.get('hits', []):
        recipes.append({
            'Label': recipe['recipe']['label'],
            'Ingredients': ', '.join(recipe['recipe']['ingredientLines']),
            'Calories': recipe['recipe'].get('calories', 0),
            'URL': recipe['recipe']['url']
        })
    
    df = pd.DataFrame(recipes)
    return df

# Function for content-based filtering using cosine similarity
def recommend_recipes(df, recipe_index):
    if df.empty:
        return []  # Return empty if DataFrame is empty

    vectorizer = CountVectorizer()
    X = vectorizer.fit_transform(df['Ingredients'])
    cosine_sim = cosine_similarity(X, X)
    
    sim_scores = list(enumerate(cosine_sim[recipe_index]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:4]  # Top 3 recommendations
    
    recommendations = []
    for i, score in sim_scores:
        similarity_percentage = round(score * 100, 2)  # Convert cosine similarity to percentage
        recommendations.append({
            'Label': df.iloc[i]['Label'],
            'URL': df.iloc[i]['URL'],
            'Similarity': f"{similarity_percentage}%"
        })
    
    return recommendations

# Route to handle the recipe search and recommendations
@app.route('/search', methods=['POST'])
def search():
    # Get user input
    query = request.form['query']
    calories = request.form['calories']
    
    # Search for recipes with calorie filtering
    recipes_df = search_recipes(query, app_id, app_key, calories)
    
    # Get recommendations based on the first result
    recommendations = recommend_recipes(recipes_df, 0) if not recipes_df.empty else []
    
    return jsonify(recommendations)

# Error handler for logging exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An error occurred: {e}")
    return "An internal error occurred", 500

if __name__ == '__main__':
    app.run(debug=True)
