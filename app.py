from flask import Flask, render_template, jsonify, request
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

# Route for Storage Page (HTML)
@app.route('/storage')
def ingredients_page():
    return render_template('storage.html')

# API to fetch ingredients from the database (GET) and add new food items (POST)
@app.route('/api/storage', methods=['GET', 'POST'])
def get_ingredients():
    cursor = db.cursor()

    if request.method == 'GET':
        # Fetch existing food storage items
        query = "SELECT foodname, quantity, expdate FROM storage WHERE userid = 1"
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

    if request.method == 'POST':
        # Get the data from the POST request (sent by the form)
        data = request.get_json()
        food_name = data['food_name']
        quantity = data['quantity']
        expiration_date = data['expiration_date']

        # Insert the new food item into the database
        insert_query = "INSERT INTO storage (userid, foodname, quantity, expdate) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (1, food_name, quantity, expiration_date))
        db.commit()

        # Return the new food item as a response
        return jsonify({
            'food_name': food_name,
            'quantity': quantity,
            'expiration_date': expiration_date
        })

if __name__ == "__main__":
    app.run(debug=True)
