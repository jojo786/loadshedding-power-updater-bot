from flask import Flask, render_template, request, url_for, flash, redirect
import os
from boto3.dynamodb.conditions import Key
from boto3 import resource
from werkzeug.exceptions import abort
import datetime
from dateutil.parser import parse
from collections import OrderedDict

dynamodb = resource('dynamodb')
power_table = dynamodb.Table(os.environ["PowerUpdaterTable"])
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dfgdfg67567jjghsdfsdi789!@##@$'

@app.route('/')
def index():
    areas = ''
    
    try: 
        response = power_table.scan()
        areas = response['Items']
    except Exception as error:
        print("dynamo scan failed:", error, flush=True) 
              
    return render_template('index.html', areas=areas) 

@app.route('/about')
def about():
    return render_template('about.html')
     

@app.route('/schedule/<string:area>')
def schedule_area(area):
    area = get_area(area)
    
    #order by date
    sorted_schedule = sorted(area['schedule'].items(), key=lambda x: parse(x[0]))
    
    return render_template('schedule_area.html', area_name=area['area'], area_stage=area['load_stage'], area_schedule=sorted_schedule)

def get_area(area):
    try:
        response = power_table.get_item(Key={'area': area})
        area = response['Item']
    except Exception as error:
        print("dynamo get post failed:", error, flush=True) 
        abort(404)

    return area