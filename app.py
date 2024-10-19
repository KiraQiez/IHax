from flask import Flask, jsonify, render_template
import pymysql

app = Flask(__name__)

# Database connection details
db = pymysql.connect(
    host="localhost",
    user="root",         
    password="",         
    database="foodwaste"  
)

# Route for Homepage (home.html)
@app.route('/')
def home_page():
    return render_template('home.html')

# Route for Ingredients Page (HTML)
@app.route('/ingredients')
def ingredients_page():
    return render_template('ingredients.html')

# API to fetch ingredients from the database
@app.route('/api/ingredients', methods=['GET'])
def get_ingredients():
    cursor = db.cursor()
    query = "SELECT food_name, quantity, expiration_date FROM ingredients WHERE user_id = 1"  # Replace user_id as needed
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

if __name__ == "__main__":
    app.run(debug=True)
