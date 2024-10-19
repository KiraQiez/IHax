from flask import Flask, request, render_template
import pymysql
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# Edamam API credentials
EDAMAM_APP_ID = "76f17ad0"
EDAMAM_APP_KEY = "0250325b6e1ecbeaa7f31ce24da04370"

# Database connection details
db = pymysql.connect(host="localhost", user="root", password="", database="foodwaste")


@app.route("/check_recipes", methods=["POST"])
def check_recipes():
    # Get the threshold for expiration (e.g., ingredients expiring in the next 3 days)
    expiry_threshold = datetime.now() + timedelta(days=3)

    # Query to fetch ingredients that are close to expiration
    cursor = db.cursor()
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
        "app_id": EDAMAM_APP_ID,
        "app_key": EDAMAM_APP_KEY,
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
                "ingredients": recipe["recipe"]["ingredientLines"],
                "image": recipe["recipe"]["image"],
            }
            for recipe in recipes
        ]
    else:
        print(f"Error fetching recipes: {response.status_code}")
        return []


if __name__ == "__main__":
    app.run(debug=True)
