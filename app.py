from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = '2a38fdd7dea359fbd744fe41'

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

# Route for Homepage (home.html)
@app.route('/')
def home_page():
    return render_template('home.html')

# Route for Login Page (HTML)
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials in the database
        cursor = db.cursor()
        cursor.execute("SELECT * FROM account WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):  # user[3] is the password column
            session['user_id'] = user[0]  # Store user ID in session
            flash('Login successful!', 'success')
            return redirect(url_for('home_page'))  # Redirect to the home page
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

# Route for Register Page (HTML)
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Insert new user into the database
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO account (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
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
    cursor = db.cursor()
    query = "SELECT foodname, quantity, expdate FROM storage WHERE userid = 1"  # Adjust user_id logic as needed
    cursor.execute(query)
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
    if calories == '1':
        calorie_range = '0-500'
    elif calories == '2':
        calorie_range = '0-1000'
    elif calories == '3':
        calorie_range = '2000+'  # More than 2000 kcal
    else:
        calorie_range = None
    
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
    
    response = requests.get(url, params=params)
    data = response.json()
    
    recipes = []
    for recipe in data.get('hits', []):
        recipes.append({
            'Label': recipe['recipe']['label'],
            'Ingredients': ', '.join(recipe['recipe']['ingredientLines']),
            'Calories': recipe['recipe'].get('calories', 0),  # Adding calories to the dataframe
            'URL': recipe['recipe']['url']
        })
    
    df = pd.DataFrame(recipes)
    return df

# Function for content-based filtering using cosine similarity
def recommend_recipes(df, recipe_index):
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
    recommendations = recommend_recipes(recipes_df, 0)
    
    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(debug=True)
