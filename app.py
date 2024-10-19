from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '2a38fdd7dea359fbd744fe41'

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
