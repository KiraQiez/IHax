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



if __name__ == "__main__":
    app.run(debug=True)
