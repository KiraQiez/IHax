from flask import Flask, render_template, jsonify, request
import pymysql
import requests
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import requests
from datetime import datetime, timedelta

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = '2a38fdd7dea359fbd744fe41'  # Replace with a secure key in production

# Database connection details

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",         
        password="",         
        database="foodwaste"
    )


# get_db_connection = pymysql.connect(
#     host="localhost",
#     user="root",         
#     password="",         
#     database="foodwaste"
# )

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

@app.route('/storage')
def storage_page():
    return render_template('storage.html')

@app.route('/magic')
def magic_page():
    user_id = 1  # Assuming a static user ID
    expiry_threshold = datetime.now() + timedelta(days=2)  # Ingredients expiring in the next 3 days

    # Fetch ingredients from the database that are close to expiration
    db = get_db_connection()
    cursor = db.cursor()
    
    query = """
    SELECT foodname FROM storage
    WHERE userid = %s AND expdate <= %s
    """
    cursor.execute(query, (user_id, expiry_threshold))
    near_expiry_ingredients = cursor.fetchall()
    cursor.close()
    
    # Convert the ingredients into a list
    ingredients = [ingredient[0] for ingredient in near_expiry_ingredients]

    # If no near-expiry ingredients, display a message
    if not ingredients:
        return render_template("magic.html", ingredients=[], recipes=[])

    # Fetch recipes using the ingredients
    recipes = get_recipes(ingredients)

    # Render the template and pass the ingredients and recipes
    return render_template('magic.html', ingredients=", ".join(ingredients), recipes=recipes)





@app.route("/check_recipes", methods=["POST"])
def check_recipes():
    # Get the threshold for expiration (e.g., ingredients expiring in the next 3 days)
    expiry_threshold = datetime.now() + timedelta(days=3)

    # Query to fetch ingredients that are close to expiration
    cursor = get_db_connection.cursor()
    query = """
    SELECT ingredient_name 
    FROM ingredients 
    WHERE expiry_date <= %s
    """
    cursor.execute(query, (expiry_threshold,))
    near_expiry_ingredients = cursor.fetchall()
    cursor.close()

    # Convert the fetched ingredients to a list
    near_expiry_ingredients = [ingredient[0] for ingredient in near_expiry_ingredients]

    # If there are no ingredients near expiry
    if not near_expiry_ingredients:
        return render_template("recommendations.html", recipes=[])

    # Call Edamam API to get recipes
    recipes = get_recipes(near_expiry_ingredients)

    return render_template("recommendations.html", recipes=recipes)


def get_recipes(ingredients):
    # Join the ingredients into a comma-separated string
    ingredients_str = ",".join(ingredients)

    # Prepare the Edamam API request
    url = "https://api.edamam.com/api/recipes/v2"
    params = {
        "type": "public",
        "q": ingredients_str,
        "app_id": app_id,
        "app_key": app_key
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        recipes = data.get("hits", [])
        # Extract relevant recipe information
        return [
            {
                "name": recipe["recipe"]["label"],
                "url": recipe["recipe"]["url"],
                "image": recipe["recipe"]["image"],
                "description": recipe["recipe"].get("description", "No description available."),
                "servings": recipe["recipe"].get("yield", "Not specified"),
                "time": recipe["recipe"].get("totalTime", "Unknown"),
            }
            for recipe in recipes
        ]
    else:
        print(f"Error fetching recipes: {response.status_code}")
        return []



# Function to search for recipes using Edamam API
def search_recipes(query, app_id, app_key, calories=None, mealType=None, cuisineType=None):
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

    # Add cuisineType filter if applicable
    if cuisineType:
        params['cuisineType'] = cuisineType

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
    cuisineType = request.form['cuisineType'] or None  # Allow None if no cuisineType

    # Search for recipes with ingredients, calorie, meal type, and cuisine type filtering
    recipes_df = search_recipes(query, app_id, app_key, calories, mealType, cuisineType)

    # Get recommendations based on the first result (content-based filtering)
    recommendations = recommend_recipes(recipes_df, 0)

    return jsonify(recommendations)


# Error handler for logging exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An error occurred: {e}")
    return "An internal error occurred", 500
@app.route('/api/storage', methods=['GET'])
def get_food_storage():
    user_id = 1  # Fixed user_id as 1
    db = get_db_connection()  # Establish a database connection
    cursor = db.cursor()

    # Define the threshold for expired items (3 days past expiration)
    expiry_threshold = datetime.now() - timedelta(days=3)

    # Delete food items that are past the expiration threshold
    delete_query = "DELETE FROM storage WHERE userid = %s AND expdate < %s"
    cursor.execute(delete_query, (user_id, expiry_threshold))
    db.commit()

    # Query to fetch remaining food storage sorted by nearest expiration date
    query = "SELECT storage_id, foodname, quantity, expdate FROM storage WHERE userid = %s ORDER BY expdate ASC"
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()

    db.close()

    # Format the result as a list of dictionaries (JSON)
    storage_items = []
    for row in rows:
        storage_items.append({
            'storage_id': row[0],
            'food_name': row[1],
            'quantity': row[2],
            'expiration_date': row[3].strftime('%Y-%m-%d')  # Format date to YYYY-MM-DD
        })

    return jsonify(storage_items)


@app.route('/api/add_food', methods=['POST'])
def add_food_item():
    user_id = 1  # Fixed user_id as there is no login system
    food_name = request.json.get('food_name')
    quantity = request.json.get('quantity')
    exp_date = request.json.get('expiration_date')

    # Make sure input data is valid
    if not food_name or not quantity or not exp_date:
        return jsonify({'message': 'Missing data!'}), 400

    db = get_db_connection()  # Establish a database connection
    cursor = db.cursor()

    query = "INSERT INTO storage (userid, foodname, quantity, expdate) VALUES (%s, %s, %s, %s)"
    try:
        cursor.execute(query, (user_id, food_name, quantity, exp_date))
        db.commit()
        # Return the added food item as a response
        return jsonify({
            'food_name': food_name,
            'quantity': quantity,
            'expiration_date': exp_date
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'message': 'Error adding food item.', 'error': str(e)}), 400
    finally:
        cursor.close()
        db.close()


@app.route('/api/remove_food', methods=['POST'])
def remove_food_item():
    user_id = 1
    storage_id = request.json['storage_id']

    db = get_db_connection()  # Establish a database connection
    cursor = db.cursor()

    query = "DELETE FROM storage WHERE userid = %s AND storage_id = %s"
    try:
        cursor.execute(query, (user_id, storage_id))
        db.commit()
        return jsonify({'message': 'Food item removed successfully!'}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'message': 'Error removing food item.', 'error': str(e)}), 400
    finally:
        db.close()


if __name__ == '__main__':
    app.run(debug=True)
