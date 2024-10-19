from flask import Flask, render_template, jsonify, request
import pymysql
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

# Route for Homepage
@app.route('/')
def home_page():
    return render_template('home.html')

@app.route('/nutrition')
def nutrition_page():
    return render_template('nutrition.html')


# Function to search for recipes using Edamam API
def search_recipes(query, app_id, app_key, calories=None, mealType=None):
    url = 'https://api.edamam.com/search'

    # Set calorie filter based on the user's input, allow no upper limit if not set
    calorie_range = f"0-{calories}" if calories else None

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

    # Add mealType filter if applicable
    if mealType:
        params['mealType'] = mealType

    # Make request to Edamam API
    response = requests.get(url, params=params)
    data = response.json()

    # Parse response into a DataFrame for further processing
    recipes = []
    for recipe in data.get('hits', []):
        recipes.append({
            'Label': recipe['recipe']['label'],
            'Ingredients': ', '.join(recipe['recipe']['ingredientLines']),
            'Calories': recipe['recipe'].get('calories', 0),
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
    sim_scores = sim_scores[1:6]  # Top 5 recommendations

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
    calories = request.form['calories'] or None  # Allow None for no upper limit
    mealType = request.form['mealType'] or None  # Allow None if no mealType

    # Search for recipes with ingredients, calorie, and meal type filtering
    recipes_df = search_recipes(query, app_id, app_key, calories, mealType)

    # Get recommendations based on the first result (content-based filtering)
    recommendations = recommend_recipes(recipes_df, 0)

    return jsonify(recommendations)

# Error handler for logging exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An error occurred: {e}")
    return "An internal error occurred", 500

if __name__ == '__main__':
    app.run(debug=True)
