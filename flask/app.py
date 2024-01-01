from flask import Flask, render_template, request, url_for, flash, redirect
import os
from boto3.dynamodb.conditions import Key
from boto3 import resource
from werkzeug.exceptions import abort
from datetime import datetime

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

@app.route('/schedule/<string:area>')
def schedule_area(area):
    area = get_area(area)
    
    return render_template('schedule_area.html', area=area)

def get_area(area):
    try:
        response = power_table.get_item(Key={'area': area})
        area = response['Item']
    except Exception as error:
        print("dynamo get post failed:", error, flush=True) 
        abort(404)

    return area
    
    for record in response['records']:
        post['id'] = record[0]['longValue']
        post['created'] = record[1]['stringValue']
        post['title'] = record[2]['stringValue']
        post['content'] = record[3]['stringValue']
    
    if len(post) == 0:
        abort(404)
    
    return post
