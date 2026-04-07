import hashlib
import json
import os
from functools import wraps
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler

from .models import User


BATTING_COLUMNS = [
    "name_x",
    "runs_x",
    "balls",
    "strike_rate",
    "fours",
    "sixes",
    "how_out",
    "run_rate",
    "team",
]

BOWLING_COLUMNS = [
    "name_x",
    "run_conceded",
    "maidens",
    "wickets",
    "overs",
    "economy",
    "wides",
    "no_balls",
    "fours",
    "sixes",
    "zeros",
    "runs",
    "over",
    "run_rate",
    "team",
]

BATTING_FEATURES = ["runs_x", "balls", "strike_rate", "fours", "sixes", "dismissal_score", "run_rate"]
BOWLING_FEATURES = [
    "run_conceded",
    "maidens",
    "wickets",
    "overs",
    "economy",
    "wides",
    "no_balls",
    "zeros",
    "run_rate",
]


BATTING_PROFILES = [
    {"name": "Virat Kohli", "team": "India", "runs": 74, "balls": 57, "strike_rate": 129, "fours": 7, "sixes": 2},
    {"name": "Rohit Sharma", "team": "India", "runs": 67, "balls": 44, "strike_rate": 152, "fours": 6, "sixes": 4},
    {"name": "Shubman Gill", "team": "India", "runs": 71, "balls": 55, "strike_rate": 128, "fours": 8, "sixes": 1},
    {"name": "KL Rahul", "team": "India", "runs": 55, "balls": 46, "strike_rate": 119, "fours": 4, "sixes": 2},
    {"name": "Suryakumar Yadav", "team": "India", "runs": 61, "balls": 33, "strike_rate": 184, "fours": 5, "sixes": 4},
    {"name": "Yashasvi Jaiswal", "team": "India", "runs": 64, "balls": 42, "strike_rate": 152, "fours": 7, "sixes": 3},
    {"name": "Steve Smith", "team": "Australia", "runs": 58, "balls": 52, "strike_rate": 111, "fours": 5, "sixes": 1},
    {"name": "David Warner", "team": "Australia", "runs": 63, "balls": 41, "strike_rate": 153, "fours": 6, "sixes": 3},
    {"name": "Travis Head", "team": "Australia", "runs": 68, "balls": 45, "strike_rate": 151, "fours": 7, "sixes": 3},
    {"name": "Marnus Labuschagne", "team": "Australia", "runs": 51, "balls": 49, "strike_rate": 104, "fours": 4, "sixes": 1},
    {"name": "Glenn Maxwell", "team": "Australia", "runs": 49, "balls": 25, "strike_rate": 196, "fours": 3, "sixes": 4},
    {"name": "Joe Root", "team": "England", "runs": 60, "balls": 53, "strike_rate": 113, "fours": 5, "sixes": 1},
    {"name": "Jos Buttler", "team": "England", "runs": 56, "balls": 34, "strike_rate": 164, "fours": 4, "sixes": 4},
    {"name": "Ben Stokes", "team": "England", "runs": 48, "balls": 35, "strike_rate": 137, "fours": 4, "sixes": 2},
    {"name": "Harry Brook", "team": "England", "runs": 59, "balls": 37, "strike_rate": 159, "fours": 5, "sixes": 3},
    {"name": "Kane Williamson", "team": "New Zealand", "runs": 57, "balls": 54, "strike_rate": 105, "fours": 4, "sixes": 1},
    {"name": "Devon Conway", "team": "New Zealand", "runs": 54, "balls": 43, "strike_rate": 125, "fours": 5, "sixes": 2},
    {"name": "Babar Azam", "team": "Pakistan", "runs": 65, "balls": 52, "strike_rate": 125, "fours": 6, "sixes": 2},
    {"name": "Mohammad Rizwan", "team": "Pakistan", "runs": 58, "balls": 47, "strike_rate": 123, "fours": 5, "sixes": 2},
    {"name": "Fakhar Zaman", "team": "Pakistan", "runs": 53, "balls": 31, "strike_rate": 170, "fours": 5, "sixes": 4},
    {"name": "Quinton de Kock", "team": "South Africa", "runs": 57, "balls": 39, "strike_rate": 146, "fours": 6, "sixes": 2},
    {"name": "Aiden Markram", "team": "South Africa", "runs": 52, "balls": 36, "strike_rate": 144, "fours": 5, "sixes": 2},
    {"name": "Heinrich Klaasen", "team": "South Africa", "runs": 62, "balls": 32, "strike_rate": 193, "fours": 5, "sixes": 4},
    {"name": "Nicholas Pooran", "team": "West Indies", "runs": 55, "balls": 31, "strike_rate": 177, "fours": 4, "sixes": 4},
]

BOWLING_PROFILES = [
    {"name": "Jasprit Bumrah", "team": "India", "run_conceded": 29, "maidens": 1, "wickets": 3, "overs": 4.0, "economy": 7.2, "wides": 1, "no_balls": 0, "zeros": 13},
    {"name": "Mohammed Shami", "team": "India", "run_conceded": 31, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
    {"name": "Mohammed Siraj", "team": "India", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 2, "no_balls": 0, "zeros": 11},
    {"name": "Kuldeep Yadav", "team": "India", "run_conceded": 26, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 6.5, "wides": 0, "no_balls": 0, "zeros": 12},
    {"name": "Ravindra Jadeja", "team": "India", "run_conceded": 24, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.0, "wides": 0, "no_balls": 0, "zeros": 13},
    {"name": "Pat Cummins", "team": "Australia", "run_conceded": 28, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.0, "wides": 1, "no_balls": 0, "zeros": 11},
    {"name": "Mitchell Starc", "team": "Australia", "run_conceded": 32, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 8.0, "wides": 2, "no_balls": 0, "zeros": 10},
    {"name": "Josh Hazlewood", "team": "Australia", "run_conceded": 27, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.7, "wides": 1, "no_balls": 0, "zeros": 12},
    {"name": "Adam Zampa", "team": "Australia", "run_conceded": 29, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.2, "wides": 0, "no_balls": 0, "zeros": 11},
    {"name": "Mark Wood", "team": "England", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 2, "no_balls": 0, "zeros": 10},
    {"name": "Jofra Archer", "team": "England", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 11},
    {"name": "Adil Rashid", "team": "England", "run_conceded": 28, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.0, "wides": 0, "no_balls": 0, "zeros": 10},
    {"name": "Trent Boult", "team": "New Zealand", "run_conceded": 27, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.7, "wides": 1, "no_balls": 0, "zeros": 12},
    {"name": "Tim Southee", "team": "New Zealand", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 10},
    {"name": "Shaheen Afridi", "team": "Pakistan", "run_conceded": 29, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.2, "wides": 1, "no_balls": 0, "zeros": 12},
    {"name": "Haris Rauf", "team": "Pakistan", "run_conceded": 34, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 8.5, "wides": 2, "no_balls": 0, "zeros": 9},
    {"name": "Rashid Khan", "team": "Afghanistan", "run_conceded": 24, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 6.0, "wides": 0, "no_balls": 0, "zeros": 13},
    {"name": "Kagiso Rabada", "team": "South Africa", "run_conceded": 28, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.0, "wides": 1, "no_balls": 0, "zeros": 11},
    {"name": "Marco Jansen", "team": "South Africa", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 2, "no_balls": 0, "zeros": 10},
    {"name": "Wanindu Hasaranga", "team": "Sri Lanka", "run_conceded": 26, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 6.5, "wides": 0, "no_balls": 0, "zeros": 12},
    {"name": "Mustafizur Rahman", "team": "Bangladesh", "run_conceded": 28, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.0, "wides": 1, "no_balls": 0, "zeros": 11},
]

IPL_BATTING_PROFILES = [
    {"name": "Virat Kohli", "team": "Royal Challengers Bengaluru", "runs": 74, "balls": 48, "strike_rate": 154, "fours": 7, "sixes": 3},
    {"name": "Rajat Patidar", "team": "Royal Challengers Bengaluru", "runs": 48, "balls": 31, "strike_rate": 155, "fours": 4, "sixes": 3},
    {"name": "Suryakumar Yadav", "team": "Mumbai Indians", "runs": 62, "balls": 34, "strike_rate": 182, "fours": 6, "sixes": 4},
    {"name": "Rohit Sharma", "team": "Mumbai Indians", "runs": 55, "balls": 37, "strike_rate": 149, "fours": 6, "sixes": 3},
    {"name": "Ruturaj Gaikwad", "team": "Chennai Super Kings", "runs": 59, "balls": 42, "strike_rate": 141, "fours": 6, "sixes": 2},
    {"name": "Shivam Dube", "team": "Chennai Super Kings", "runs": 44, "balls": 25, "strike_rate": 176, "fours": 3, "sixes": 4},
    {"name": "Shreyas Iyer", "team": "Kolkata Knight Riders", "runs": 52, "balls": 38, "strike_rate": 137, "fours": 5, "sixes": 2},
    {"name": "Rinku Singh", "team": "Kolkata Knight Riders", "runs": 43, "balls": 24, "strike_rate": 179, "fours": 3, "sixes": 4},
    {"name": "Travis Head", "team": "Sunrisers Hyderabad", "runs": 67, "balls": 36, "strike_rate": 186, "fours": 7, "sixes": 4},
    {"name": "Abhishek Sharma", "team": "Sunrisers Hyderabad", "runs": 50, "balls": 28, "strike_rate": 178, "fours": 5, "sixes": 4},
    {"name": "Sanju Samson", "team": "Rajasthan Royals", "runs": 56, "balls": 36, "strike_rate": 156, "fours": 5, "sixes": 3},
    {"name": "Yashasvi Jaiswal", "team": "Rajasthan Royals", "runs": 61, "balls": 39, "strike_rate": 156, "fours": 7, "sixes": 3},
    {"name": "Rishabh Pant", "team": "Delhi Capitals", "runs": 50, "balls": 31, "strike_rate": 161, "fours": 4, "sixes": 3},
    {"name": "Jake Fraser-McGurk", "team": "Delhi Capitals", "runs": 47, "balls": 23, "strike_rate": 204, "fours": 5, "sixes": 4},
    {"name": "Shubman Gill", "team": "Gujarat Titans", "runs": 65, "balls": 45, "strike_rate": 144, "fours": 7, "sixes": 2},
    {"name": "Sai Sudharsan", "team": "Gujarat Titans", "runs": 54, "balls": 40, "strike_rate": 135, "fours": 5, "sixes": 2},
    {"name": "KL Rahul", "team": "Lucknow Super Giants", "runs": 57, "balls": 43, "strike_rate": 133, "fours": 5, "sixes": 2},
    {"name": "Nicholas Pooran", "team": "Lucknow Super Giants", "runs": 48, "balls": 25, "strike_rate": 192, "fours": 3, "sixes": 5},
    {"name": "Shashank Singh", "team": "Punjab Kings", "runs": 46, "balls": 27, "strike_rate": 170, "fours": 4, "sixes": 3},
    {"name": "Prabhsimran Singh", "team": "Punjab Kings", "runs": 44, "balls": 28, "strike_rate": 157, "fours": 5, "sixes": 2},
]

IPL_BOWLING_PROFILES = [
    {"name": "Jasprit Bumrah", "team": "Mumbai Indians", "run_conceded": 27, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 6.7, "wides": 1, "no_balls": 0, "zeros": 13},
    {"name": "Piyush Chawla", "team": "Mumbai Indians", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 10},
    {"name": "Mohammed Siraj", "team": "Royal Challengers Bengaluru", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 2, "no_balls": 0, "zeros": 10},
    {"name": "Yash Dayal", "team": "Royal Challengers Bengaluru", "run_conceded": 32, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 8.0, "wides": 1, "no_balls": 0, "zeros": 9},
    {"name": "Ravindra Jadeja", "team": "Chennai Super Kings", "run_conceded": 25, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.2, "wides": 0, "no_balls": 0, "zeros": 12},
    {"name": "Matheesha Pathirana", "team": "Chennai Super Kings", "run_conceded": 30, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.5, "wides": 2, "no_balls": 0, "zeros": 11},
    {"name": "Sunil Narine", "team": "Kolkata Knight Riders", "run_conceded": 24, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.0, "wides": 0, "no_balls": 0, "zeros": 13},
    {"name": "Varun Chakravarthy", "team": "Kolkata Knight Riders", "run_conceded": 28, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.0, "wides": 0, "no_balls": 0, "zeros": 12},
    {"name": "Pat Cummins", "team": "Sunrisers Hyderabad", "run_conceded": 29, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.2, "wides": 1, "no_balls": 0, "zeros": 11},
    {"name": "T Natarajan", "team": "Sunrisers Hyderabad", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
    {"name": "Yuzvendra Chahal", "team": "Rajasthan Royals", "run_conceded": 28, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.0, "wides": 0, "no_balls": 0, "zeros": 11},
    {"name": "Trent Boult", "team": "Rajasthan Royals", "run_conceded": 27, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.7, "wides": 1, "no_balls": 0, "zeros": 12},
    {"name": "Kuldeep Yadav", "team": "Delhi Capitals", "run_conceded": 26, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 6.5, "wides": 0, "no_balls": 0, "zeros": 12},
    {"name": "Axar Patel", "team": "Delhi Capitals", "run_conceded": 25, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.2, "wides": 0, "no_balls": 0, "zeros": 12},
    {"name": "Rashid Khan", "team": "Gujarat Titans", "run_conceded": 24, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 6.0, "wides": 0, "no_balls": 0, "zeros": 13},
    {"name": "Mohit Sharma", "team": "Gujarat Titans", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 10},
    {"name": "Ravi Bishnoi", "team": "Lucknow Super Giants", "run_conceded": 27, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.7, "wides": 0, "no_balls": 0, "zeros": 12},
    {"name": "Mayank Yadav", "team": "Lucknow Super Giants", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 2, "no_balls": 0, "zeros": 10},
    {"name": "Arshdeep Singh", "team": "Punjab Kings", "run_conceded": 30, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 11},
    {"name": "Kagiso Rabada", "team": "Punjab Kings", "run_conceded": 29, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.2, "wides": 1, "no_balls": 0, "zeros": 11},
]

IPL_BATTING_PROFILES.extend(
    [
        {"name": "Phil Salt", "team": "Royal Challengers Bengaluru", "runs": 46, "balls": 27, "strike_rate": 170, "fours": 5, "sixes": 3},
        {"name": "Liam Livingstone", "team": "Royal Challengers Bengaluru", "runs": 39, "balls": 22, "strike_rate": 177, "fours": 3, "sixes": 4},
        {"name": "Jitesh Sharma", "team": "Royal Challengers Bengaluru", "runs": 34, "balls": 21, "strike_rate": 162, "fours": 3, "sixes": 3},
        {"name": "Tilak Varma", "team": "Mumbai Indians", "runs": 49, "balls": 32, "strike_rate": 153, "fours": 5, "sixes": 2},
        {"name": "Hardik Pandya", "team": "Mumbai Indians", "runs": 38, "balls": 23, "strike_rate": 165, "fours": 3, "sixes": 3},
        {"name": "Naman Dhir", "team": "Mumbai Indians", "runs": 36, "balls": 24, "strike_rate": 150, "fours": 4, "sixes": 2},
        {"name": "Devon Conway", "team": "Chennai Super Kings", "runs": 52, "balls": 39, "strike_rate": 133, "fours": 5, "sixes": 2},
        {"name": "Ravindra Jadeja", "team": "Chennai Super Kings", "runs": 35, "balls": 23, "strike_rate": 152, "fours": 3, "sixes": 2},
        {"name": "MS Dhoni", "team": "Chennai Super Kings", "runs": 29, "balls": 16, "strike_rate": 181, "fours": 2, "sixes": 3},
        {"name": "Sunil Narine", "team": "Kolkata Knight Riders", "runs": 43, "balls": 24, "strike_rate": 179, "fours": 4, "sixes": 4},
        {"name": "Andre Russell", "team": "Kolkata Knight Riders", "runs": 41, "balls": 20, "strike_rate": 205, "fours": 3, "sixes": 5},
        {"name": "Venkatesh Iyer", "team": "Kolkata Knight Riders", "runs": 47, "balls": 33, "strike_rate": 142, "fours": 5, "sixes": 2},
        {"name": "Heinrich Klaasen", "team": "Sunrisers Hyderabad", "runs": 56, "balls": 28, "strike_rate": 200, "fours": 4, "sixes": 5},
        {"name": "Nitish Kumar Reddy", "team": "Sunrisers Hyderabad", "runs": 42, "balls": 27, "strike_rate": 156, "fours": 4, "sixes": 3},
        {"name": "Ishan Kishan", "team": "Sunrisers Hyderabad", "runs": 45, "balls": 29, "strike_rate": 155, "fours": 5, "sixes": 2},
        {"name": "Riyan Parag", "team": "Rajasthan Royals", "runs": 50, "balls": 32, "strike_rate": 156, "fours": 5, "sixes": 3},
        {"name": "Shimron Hetmyer", "team": "Rajasthan Royals", "runs": 38, "balls": 22, "strike_rate": 173, "fours": 3, "sixes": 4},
        {"name": "Dhruv Jurel", "team": "Rajasthan Royals", "runs": 35, "balls": 24, "strike_rate": 146, "fours": 3, "sixes": 2},
        {"name": "Tristan Stubbs", "team": "Delhi Capitals", "runs": 44, "balls": 27, "strike_rate": 163, "fours": 4, "sixes": 3},
        {"name": "Abishek Porel", "team": "Delhi Capitals", "runs": 40, "balls": 28, "strike_rate": 143, "fours": 5, "sixes": 2},
        {"name": "Axar Patel", "team": "Delhi Capitals", "runs": 37, "balls": 24, "strike_rate": 154, "fours": 3, "sixes": 3},
        {"name": "Jos Buttler", "team": "Gujarat Titans", "runs": 58, "balls": 36, "strike_rate": 161, "fours": 6, "sixes": 3},
        {"name": "Rahul Tewatia", "team": "Gujarat Titans", "runs": 36, "balls": 20, "strike_rate": 180, "fours": 3, "sixes": 3},
        {"name": "Shahrukh Khan", "team": "Gujarat Titans", "runs": 34, "balls": 21, "strike_rate": 162, "fours": 3, "sixes": 3},
        {"name": "Aiden Markram", "team": "Lucknow Super Giants", "runs": 43, "balls": 31, "strike_rate": 139, "fours": 4, "sixes": 2},
        {"name": "David Miller", "team": "Lucknow Super Giants", "runs": 41, "balls": 25, "strike_rate": 164, "fours": 3, "sixes": 3},
        {"name": "Ayush Badoni", "team": "Lucknow Super Giants", "runs": 35, "balls": 24, "strike_rate": 146, "fours": 3, "sixes": 2},
        {"name": "Shreyas Iyer", "team": "Punjab Kings", "runs": 51, "balls": 37, "strike_rate": 138, "fours": 5, "sixes": 2},
        {"name": "Glenn Maxwell", "team": "Punjab Kings", "runs": 39, "balls": 22, "strike_rate": 177, "fours": 3, "sixes": 4},
        {"name": "Marcus Stoinis", "team": "Punjab Kings", "runs": 42, "balls": 26, "strike_rate": 162, "fours": 4, "sixes": 3},
    ]
)

IPL_BOWLING_PROFILES.extend(
    [
        {"name": "Bhuvneshwar Kumar", "team": "Royal Challengers Bengaluru", "run_conceded": 29, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.2, "wides": 1, "no_balls": 0, "zeros": 11},
        {"name": "Krunal Pandya", "team": "Royal Challengers Bengaluru", "run_conceded": 27, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.7, "wides": 0, "no_balls": 0, "zeros": 12},
        {"name": "Josh Hazlewood", "team": "Royal Challengers Bengaluru", "run_conceded": 28, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.0, "wides": 1, "no_balls": 0, "zeros": 12},
        {"name": "Trent Boult", "team": "Mumbai Indians", "run_conceded": 28, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.0, "wides": 1, "no_balls": 0, "zeros": 12},
        {"name": "Deepak Chahar", "team": "Mumbai Indians", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Hardik Pandya", "team": "Mumbai Indians", "run_conceded": 33, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 8.2, "wides": 1, "no_balls": 0, "zeros": 9},
        {"name": "Noor Ahmad", "team": "Chennai Super Kings", "run_conceded": 27, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.7, "wides": 0, "no_balls": 0, "zeros": 12},
        {"name": "Khaleel Ahmed", "team": "Chennai Super Kings", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Ravichandran Ashwin", "team": "Chennai Super Kings", "run_conceded": 26, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.5, "wides": 0, "no_balls": 0, "zeros": 12},
        {"name": "Harshit Rana", "team": "Kolkata Knight Riders", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Andre Russell", "team": "Kolkata Knight Riders", "run_conceded": 32, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 8.0, "wides": 2, "no_balls": 0, "zeros": 9},
        {"name": "Anrich Nortje", "team": "Kolkata Knight Riders", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Mohammed Shami", "team": "Sunrisers Hyderabad", "run_conceded": 28, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.0, "wides": 1, "no_balls": 0, "zeros": 12},
        {"name": "Harshal Patel", "team": "Sunrisers Hyderabad", "run_conceded": 32, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 8.0, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Adam Zampa", "team": "Sunrisers Hyderabad", "run_conceded": 29, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.2, "wides": 0, "no_balls": 0, "zeros": 11},
        {"name": "Jofra Archer", "team": "Rajasthan Royals", "run_conceded": 29, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.2, "wides": 1, "no_balls": 0, "zeros": 11},
        {"name": "Wanindu Hasaranga", "team": "Rajasthan Royals", "run_conceded": 27, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.7, "wides": 0, "no_balls": 0, "zeros": 12},
        {"name": "Sandeep Sharma", "team": "Rajasthan Royals", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Mitchell Starc", "team": "Delhi Capitals", "run_conceded": 31, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 11},
        {"name": "Mukesh Kumar", "team": "Delhi Capitals", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "T Natarajan", "team": "Delhi Capitals", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Mohammed Siraj", "team": "Gujarat Titans", "run_conceded": 29, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.2, "wides": 1, "no_balls": 0, "zeros": 11},
        {"name": "Prasidh Krishna", "team": "Gujarat Titans", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "R Sai Kishore", "team": "Gujarat Titans", "run_conceded": 26, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 6.5, "wides": 0, "no_balls": 0, "zeros": 12},
        {"name": "Avesh Khan", "team": "Lucknow Super Giants", "run_conceded": 31, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.7, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Shardul Thakur", "team": "Lucknow Super Giants", "run_conceded": 32, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 8.0, "wides": 1, "no_balls": 0, "zeros": 9},
        {"name": "Shahbaz Ahmed", "team": "Lucknow Super Giants", "run_conceded": 28, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.0, "wides": 0, "no_balls": 0, "zeros": 11},
        {"name": "Yuzvendra Chahal", "team": "Punjab Kings", "run_conceded": 27, "maidens": 0, "wickets": 3, "overs": 4.0, "economy": 6.7, "wides": 0, "no_balls": 0, "zeros": 12},
        {"name": "Marco Jansen", "team": "Punjab Kings", "run_conceded": 30, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 7.5, "wides": 1, "no_balls": 0, "zeros": 10},
        {"name": "Lockie Ferguson", "team": "Punjab Kings", "run_conceded": 32, "maidens": 0, "wickets": 2, "overs": 4.0, "economy": 8.0, "wides": 1, "no_balls": 0, "zeros": 9},
    ]
)

BATTING_PROFILES.extend(IPL_BATTING_PROFILES)
BOWLING_PROFILES.extend(IPL_BOWLING_PROFILES)

IPL_STATIC_FIXTURES = [
    {
        "date": "2026-04-08",
        "time": "19:30",
        "name": "Delhi Capitals vs Gujarat Titans",
        "teams": ["Delhi Capitals", "Gujarat Titans"],
        "venue": "Arun Jaitley Stadium, Delhi",
    },
    {
        "date": "2026-04-09",
        "time": "19:30",
        "name": "Kolkata Knight Riders vs Lucknow Super Giants",
        "teams": ["Kolkata Knight Riders", "Lucknow Super Giants"],
        "venue": "Eden Gardens, Kolkata",
    },
    {
        "date": "2026-04-10",
        "time": "19:30",
        "name": "Rajasthan Royals vs Royal Challengers Bengaluru",
        "teams": ["Rajasthan Royals", "Royal Challengers Bengaluru"],
        "venue": "Barsapara Cricket Stadium, Guwahati",
    },
    {
        "date": "2026-04-11",
        "time": "15:30",
        "name": "Punjab Kings vs Sunrisers Hyderabad",
        "teams": ["Punjab Kings", "Sunrisers Hyderabad"],
        "venue": "Maharaja Yadavindra Singh International Cricket Stadium, New Chandigarh",
    },
    {
        "date": "2026-04-11",
        "time": "19:30",
        "name": "Chennai Super Kings vs Delhi Capitals",
        "teams": ["Chennai Super Kings", "Delhi Capitals"],
        "venue": "MA Chidambaram Stadium, Chennai",
    },
    {
        "date": "2026-04-12",
        "time": "15:30",
        "name": "Lucknow Super Giants vs Gujarat Titans",
        "teams": ["Lucknow Super Giants", "Gujarat Titans"],
        "venue": "Ekana Cricket Stadium, Lucknow",
    },
    {
        "date": "2026-04-12",
        "time": "19:30",
        "name": "Mumbai Indians vs Royal Challengers Bengaluru",
        "teams": ["Mumbai Indians", "Royal Challengers Bengaluru"],
        "venue": "Wankhede Stadium, Mumbai",
    },
    {
        "date": "2026-04-13",
        "time": "19:30",
        "name": "Sunrisers Hyderabad vs Rajasthan Royals",
        "teams": ["Sunrisers Hyderabad", "Rajasthan Royals"],
        "venue": "Rajiv Gandhi International Stadium, Hyderabad",
    },
    {
        "date": "2026-04-14",
        "time": "19:30",
        "name": "Chennai Super Kings vs Kolkata Knight Riders",
        "teams": ["Chennai Super Kings", "Kolkata Knight Riders"],
        "venue": "MA Chidambaram Stadium, Chennai",
    },
    {
        "date": "2026-04-15",
        "time": "19:30",
        "name": "Royal Challengers Bengaluru vs Lucknow Super Giants",
        "teams": ["Royal Challengers Bengaluru", "Lucknow Super Giants"],
        "venue": "M Chinnaswamy Stadium, Bengaluru",
    },
    {
        "date": "2026-04-16",
        "time": "19:30",
        "name": "Mumbai Indians vs Punjab Kings",
        "teams": ["Mumbai Indians", "Punjab Kings"],
        "venue": "Wankhede Stadium, Mumbai",
    },
    {
        "date": "2026-04-17",
        "time": "19:30",
        "name": "Gujarat Titans vs Kolkata Knight Riders",
        "teams": ["Gujarat Titans", "Kolkata Knight Riders"],
        "venue": "Narendra Modi Stadium, Ahmedabad",
    },
    {
        "date": "2026-04-18",
        "time": "15:30",
        "name": "Royal Challengers Bengaluru vs Delhi Capitals",
        "teams": ["Royal Challengers Bengaluru", "Delhi Capitals"],
        "venue": "M Chinnaswamy Stadium, Bengaluru",
    },
]

FALLBACK_FIXTURES = [
    {
        "name": "India vs Australia",
        "match_type": "ODI",
        "series": "CricPredict Demo Series",
        "venue": "Wankhede Stadium, Mumbai",
        "teams": ["India", "Australia"],
    },
    {
        "name": "England vs Pakistan",
        "match_type": "T20",
        "series": "CricPredict Demo Series",
        "venue": "Lord's Cricket Ground, London",
        "teams": ["England", "Pakistan"],
    },
    {
        "name": "South Africa vs New Zealand",
        "match_type": "ODI",
        "series": "CricPredict Demo Series",
        "venue": "Newlands Cricket Ground, Cape Town",
        "teams": ["South Africa", "New Zealand"],
    },
]


def stable_seed(label):
    digest = hashlib.md5(label.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def rng_for(label):
    return np.random.default_rng(stable_seed(label))


def normalize_minmax(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    minimum = float(series.min())
    maximum = float(series.max())
    if maximum - minimum == 0:
        return pd.Series(np.ones(len(series)) * 0.5, index=series.index)
    return (series - minimum) / (maximum - minimum)


def safe_float(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(number) or np.isinf(number):
        return default
    return number


def top_up_players(primary, fallback, limit):
    selected = list(primary)
    seen = {(player["name"], player["team"]) for player in selected}
    for player in fallback:
        key = (player["name"], player["team"])
        if key in seen:
            continue
        selected.append(player)
        seen.add(key)
        if len(selected) >= limit:
            break
    for rank, player in enumerate(selected, start=1):
        player["rank"] = rank
    return selected[:limit]


def add_message(context, text=None, level="info"):
    context["message"] = text
    context["message_level"] = level
    return context


def is_safe_local_path(path):
    return bool(path) and path.startswith("/") and not path.startswith("//")


def current_user(request):
    session = getattr(request, "session", None)
    if session is None:
        return None
    user_id = session.get("app_user_id")
    if not user_id:
        return None
    return User.objects.filter(id=user_id).first()


def require_login(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not current_user(request):
            login_url = f"{reverse('UserLogin')}?{urlencode({'next': request.get_full_path()})}"
            return redirect(login_url)
        return view_func(request, *args, **kwargs)

    return wrapped


def load_csv(path, expected_columns):
    if not os.path.exists(path):
        return pd.DataFrame(columns=expected_columns)

    frame = pd.read_csv(path)
    for column in expected_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    return frame[expected_columns].copy()


def build_batsman_rows(profile, samples=8):
    rng = rng_for(f"bat-{profile['name']}")
    rows = []
    outs = ["caught", "bowled", "lbw", "run out", "not out"]
    for _ in range(samples):
        runs = int(np.clip(rng.normal(profile["runs"], 12), 18, 145))
        balls = int(np.clip(rng.normal(profile["balls"], 8), 15, 120))
        strike_rate = round(max(70.0, (runs / max(balls, 1)) * 100 + rng.normal(0, 6)), 2)
        fours = int(np.clip(rng.normal(profile["fours"], 1.6), 1, 16))
        sixes = int(np.clip(rng.normal(profile["sixes"], 1.2), 0, 8))
        run_rate = round((runs / max(balls, 1)) * 6, 2)
        rows.append(
            {
                "name_x": profile["name"],
                "runs_x": runs,
                "balls": balls,
                "strike_rate": strike_rate,
                "fours": fours,
                "sixes": sixes,
                "how_out": rng.choice(outs, p=[0.34, 0.16, 0.14, 0.06, 0.30]),
                "run_rate": run_rate,
                "team": profile["team"],
            }
        )
    return rows


def build_bowler_rows(profile, samples=8):
    rng = rng_for(f"ball-{profile['name']}")
    rows = []
    for _ in range(samples):
        overs = round(float(np.clip(rng.normal(profile["overs"], 0.2), 3.0, 4.0)), 1)
        runs_conceded = int(np.clip(rng.normal(profile["run_conceded"], 5), 15, 48))
        wickets = int(np.clip(rng.normal(profile["wickets"], 1), 0, 5))
        maidens = int(np.clip(rng.normal(profile["maidens"], 0.6), 0, 2))
        economy = round(max(4.2, runs_conceded / max(overs, 1.0)), 2)
        wides = int(np.clip(rng.normal(profile["wides"], 0.7), 0, 4))
        no_balls = int(np.clip(rng.normal(profile["no_balls"], 0.3), 0, 2))
        zeros = int(np.clip(rng.normal(profile["zeros"], 2.0), 5, 18))
        runs = int(np.clip(rng.normal(10, 6), 0, 28))
        boundaries_fours = int(np.clip(rng.normal(3, 1.2), 0, 7))
        boundaries_sixes = int(np.clip(rng.normal(1, 0.8), 0, 4))
        rows.append(
            {
                "name_x": profile["name"],
                "run_conceded": runs_conceded,
                "maidens": maidens,
                "wickets": wickets,
                "overs": overs,
                "economy": economy,
                "wides": wides,
                "no_balls": no_balls,
                "fours": boundaries_fours,
                "sixes": boundaries_sixes,
                "zeros": zeros,
                "runs": runs,
                "over": overs,
                "run_rate": economy,
                "team": profile["team"],
            }
        )
    return rows


def enrich_batting_frame(frame, minimum_players=20, samples=6):
    frame = frame.copy()
    if "team" not in frame.columns:
        frame["team"] = np.nan
    frame["team"] = frame["team"].astype("object")

    known = {}
    for profile in BATTING_PROFILES:
        known[profile["name"]] = profile["team"]

    for name, team in known.items():
        frame.loc[frame["name_x"].astype(str) == name, "team"] = team

    existing_names = set(frame["name_x"].dropna().astype(str))
    needed_profiles = BATTING_PROFILES
    if len(existing_names) >= minimum_players:
        needed_profiles = [profile for profile in BATTING_PROFILES if profile["name"] not in existing_names]

    synthetic_rows = []
    for profile in needed_profiles:
        if profile["name"] not in existing_names or len(existing_names) < minimum_players:
            synthetic_rows.extend(build_batsman_rows(profile, samples=samples))
            existing_names.add(profile["name"])

    if synthetic_rows:
        frame = pd.concat([frame, pd.DataFrame(synthetic_rows)], ignore_index=True)

    existing_pairs = set(
        zip(
            frame["name_x"].fillna("").astype(str),
            frame["team"].fillna("").astype(str),
        )
    )
    ipl_rows = []
    for profile in IPL_BATTING_PROFILES:
        if (profile["name"], profile["team"]) not in existing_pairs:
            ipl_rows.extend(build_batsman_rows(profile, samples=samples))
    if ipl_rows:
        frame = pd.concat([frame, pd.DataFrame(ipl_rows)], ignore_index=True)

    frame["name_x"] = frame["name_x"].astype(str)
    frame["team"] = frame["team"].fillna("International")
    frame["how_out"] = frame["how_out"].fillna("caught").astype(str)
    frame["runs_x"] = pd.to_numeric(frame["runs_x"], errors="coerce").fillna(0)
    frame["balls"] = pd.to_numeric(frame["balls"], errors="coerce").replace(0, np.nan)
    frame["strike_rate"] = pd.to_numeric(frame["strike_rate"], errors="coerce")
    frame["fours"] = pd.to_numeric(frame["fours"], errors="coerce").fillna(0)
    frame["sixes"] = pd.to_numeric(frame["sixes"], errors="coerce").fillna(0)
    if "run_rate" not in frame.columns:
        frame["run_rate"] = np.nan
    frame["run_rate"] = pd.to_numeric(frame["run_rate"], errors="coerce")
    frame["balls"] = frame["balls"].fillna(np.maximum(frame["runs_x"] / 1.25, 1))
    frame["strike_rate"] = frame["strike_rate"].fillna((frame["runs_x"] / frame["balls"]) * 100)
    frame["run_rate"] = frame["run_rate"].fillna((frame["runs_x"] / frame["balls"]) * 6)
    frame["dismissal_score"] = np.where(frame["how_out"].str.lower() == "not out", 1.0, 0.35)
    return frame


def enrich_bowling_frame(frame, minimum_players=20, samples=6):
    frame = frame.copy()
    if "team" not in frame.columns:
        frame["team"] = np.nan
    frame["team"] = frame["team"].astype("object")

    known = {}
    for profile in BOWLING_PROFILES:
        known[profile["name"]] = profile["team"]

    for name, team in known.items():
        frame.loc[frame["name_x"].astype(str) == name, "team"] = team

    existing_names = set(frame["name_x"].dropna().astype(str))
    needed_profiles = BOWLING_PROFILES
    if len(existing_names) >= minimum_players:
        needed_profiles = [profile for profile in BOWLING_PROFILES if profile["name"] not in existing_names]

    synthetic_rows = []
    for profile in needed_profiles:
        if profile["name"] not in existing_names or len(existing_names) < minimum_players:
            synthetic_rows.extend(build_bowler_rows(profile, samples=samples))
            existing_names.add(profile["name"])

    if synthetic_rows:
        frame = pd.concat([frame, pd.DataFrame(synthetic_rows)], ignore_index=True)

    existing_pairs = set(
        zip(
            frame["name_x"].fillna("").astype(str),
            frame["team"].fillna("").astype(str),
        )
    )
    ipl_rows = []
    for profile in IPL_BOWLING_PROFILES:
        if (profile["name"], profile["team"]) not in existing_pairs:
            ipl_rows.extend(build_bowler_rows(profile, samples=samples))
    if ipl_rows:
        frame = pd.concat([frame, pd.DataFrame(ipl_rows)], ignore_index=True)

    numeric_columns = [
        "run_conceded",
        "maidens",
        "wickets",
        "overs",
        "economy",
        "wides",
        "no_balls",
        "fours",
        "sixes",
        "zeros",
        "runs",
        "over",
        "run_rate",
    ]
    frame["name_x"] = frame["name_x"].astype(str)
    frame["team"] = frame["team"].fillna("International")
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    frame["overs"] = frame["overs"].where(frame["overs"] > 0, frame["over"])
    frame["overs"] = frame["overs"].where(frame["overs"] > 0, 4.0)
    frame["economy"] = frame["economy"].where(frame["economy"] > 0, frame["run_conceded"] / frame["overs"].replace(0, 1))
    frame["run_rate"] = frame["run_rate"].where(frame["run_rate"] > 0, frame["economy"])
    return frame


def team_matches(player_team, requested_teams):
    if not requested_teams:
        return True
    player_team_text = player_team.lower()
    for team in requested_teams:
        team_text = team.lower()
        if player_team_text in team_text or team_text in player_team_text:
            return True
    return False


def fit_state_model(train_frame, features, target_score):
    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_frame[features])
    component_count = max(2, min(6, len(train_frame) // 15))
    model = hmm.GaussianHMM(
        n_components=component_count,
        covariance_type="diag",
        n_iter=250,
        random_state=42,
    )
    model.fit(X_train)
    states = model.predict(X_train)
    state_quality = {}
    for state in np.unique(states):
        state_quality[state] = float(target_score[states == state].mean())
    return scaler, model, state_quality


def aggregate_predictions(frame, name_column, team_column, score_column, stat_columns):
    frame = frame.copy()
    frame[score_column] = pd.to_numeric(frame[score_column], errors="coerce").fillna(0)
    aggregate_map = {score_column: "mean"}
    for column in stat_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
        aggregate_map[column] = "mean"
    grouped = (
        frame.groupby([name_column, team_column], as_index=False)
        .agg(aggregate_map)
        .sort_values(score_column, ascending=False)
        .reset_index(drop=True)
    )
    grouped["rank"] = grouped.index + 1
    grouped["display_score"] = (grouped[score_column].clip(lower=0, upper=1) * 100).round(1)
    return grouped


def compute_batsman_predictions(limit=15, teams=None):
    base_dir = os.path.dirname(__file__)
    train_path = os.path.join(base_dir, "..", "Dataset", "bat.csv")
    test_path = os.path.join(base_dir, "..", "Dataset", "test_bat.csv")

    train_frame = enrich_batting_frame(load_csv(train_path, BATTING_COLUMNS), minimum_players=24, samples=7)
    candidate_frame = enrich_batting_frame(load_csv(test_path, BATTING_COLUMNS), minimum_players=24, samples=5)

    if teams:
        filtered = candidate_frame[candidate_frame["team"].apply(lambda value: team_matches(value, teams))]
        if len(filtered["name_x"].unique()) >= 4:
            candidate_frame = filtered.reset_index(drop=True)
    else:
        candidate_frame = candidate_frame.reset_index(drop=True)

    base_score = (
        normalize_minmax(train_frame["runs_x"]) * 0.42
        + normalize_minmax(train_frame["strike_rate"]) * 0.23
        + normalize_minmax(train_frame["run_rate"]) * 0.10
        + normalize_minmax(train_frame["fours"] + train_frame["sixes"] * 1.5) * 0.15
        + train_frame["dismissal_score"] * 0.10
    )
    scaler, model, state_quality = fit_state_model(train_frame, BATTING_FEATURES, base_score.to_numpy())

    candidate_base = (
        normalize_minmax(candidate_frame["runs_x"]) * 0.42
        + normalize_minmax(candidate_frame["strike_rate"]) * 0.23
        + normalize_minmax(candidate_frame["run_rate"]) * 0.10
        + normalize_minmax(candidate_frame["fours"] + candidate_frame["sixes"] * 1.5) * 0.15
        + candidate_frame["dismissal_score"] * 0.10
    )
    candidate_states = model.predict(scaler.transform(candidate_frame[BATTING_FEATURES]))
    state_scores = pd.Series(candidate_states, index=candidate_frame.index).map(state_quality)
    state_scores = state_scores.fillna(safe_float(candidate_base.mean()))
    candidate_frame["prediction_score"] = (
        candidate_base * 0.72 + state_scores * 0.28
    )

    predictions = aggregate_predictions(
        candidate_frame,
        "name_x",
        "team",
        "prediction_score",
        ["runs_x", "strike_rate", "fours", "sixes"],
    ).head(limit)
    return [
        {
            "rank": int(row["rank"]),
            "name": row["name_x"],
            "team": row["team"],
            "score": round(safe_float(row["display_score"]), 1),
            "metric_label": "Avg Runs",
            "metric_value": f"{safe_float(row['runs_x']):.1f}",
            "detail": f"SR {safe_float(row['strike_rate']):.1f} | Boundaries {(safe_float(row['fours']) + safe_float(row['sixes'])):.1f}",
        }
        for _, row in predictions.iterrows()
    ]


def compute_bowler_predictions(limit=15, teams=None):
    base_dir = os.path.dirname(__file__)
    train_path = os.path.join(base_dir, "..", "Dataset", "ball.csv")
    test_path = os.path.join(base_dir, "..", "Dataset", "test_ball.csv")

    train_frame = enrich_bowling_frame(load_csv(train_path, BOWLING_COLUMNS), minimum_players=20, samples=7)
    candidate_frame = enrich_bowling_frame(load_csv(test_path, BOWLING_COLUMNS), minimum_players=20, samples=5)

    if teams:
        filtered = candidate_frame[candidate_frame["team"].apply(lambda value: team_matches(value, teams))]
        if len(filtered["name_x"].unique()) >= 4:
            candidate_frame = filtered.reset_index(drop=True)
    else:
        candidate_frame = candidate_frame.reset_index(drop=True)

    base_score = (
        normalize_minmax(train_frame["wickets"]) * 0.38
        + normalize_minmax(train_frame["maidens"]) * 0.08
        + (1 - normalize_minmax(train_frame["economy"])) * 0.22
        + (1 - normalize_minmax(train_frame["run_conceded"])) * 0.12
        + normalize_minmax(train_frame["zeros"]) * 0.12
        + (1 - normalize_minmax(train_frame["wides"] + train_frame["no_balls"])) * 0.08
    )
    scaler, model, state_quality = fit_state_model(train_frame, BOWLING_FEATURES, base_score.to_numpy())

    candidate_base = (
        normalize_minmax(candidate_frame["wickets"]) * 0.38
        + normalize_minmax(candidate_frame["maidens"]) * 0.08
        + (1 - normalize_minmax(candidate_frame["economy"])) * 0.22
        + (1 - normalize_minmax(candidate_frame["run_conceded"])) * 0.12
        + normalize_minmax(candidate_frame["zeros"]) * 0.12
        + (1 - normalize_minmax(candidate_frame["wides"] + candidate_frame["no_balls"])) * 0.08
    )
    candidate_states = model.predict(scaler.transform(candidate_frame[BOWLING_FEATURES]))
    state_scores = pd.Series(candidate_states, index=candidate_frame.index).map(state_quality)
    state_scores = state_scores.fillna(safe_float(candidate_base.mean()))
    candidate_frame["prediction_score"] = (
        candidate_base * 0.7 + state_scores * 0.3
    )

    predictions = aggregate_predictions(
        candidate_frame,
        "name_x",
        "team",
        "prediction_score",
        ["wickets", "economy", "zeros", "maidens"],
    ).head(limit)
    return [
        {
            "rank": int(row["rank"]),
            "name": row["name_x"],
            "team": row["team"],
            "score": round(safe_float(row["display_score"]), 1),
            "metric_label": "Avg Wickets",
            "metric_value": f"{safe_float(row['wickets']):.1f}",
            "detail": f"Econ {safe_float(row['economy']):.1f} | Dot Balls {safe_float(row['zeros']):.1f}",
        }
        for _, row in predictions.iterrows()
    ]


def parse_fixture_datetime(raw_value):
    if not raw_value:
        return None
    candidates = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y %H:%M",
    ]
    text = str(raw_value).replace("Z", "")
    for pattern in candidates:
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def format_fixture_datetime(start_dt):
    if not start_dt:
        return "Schedule pending"
    return start_dt.strftime("%d %b %Y, %I:%M %p UTC")


def build_fallback_fixture(reason):
    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    next_ipl_fixture = None
    next_ipl_datetime = None
    for fixture in IPL_STATIC_FIXTURES:
        fixture_datetime = datetime.strptime(f"{fixture['date']} {fixture['time']}", "%Y-%m-%d %H:%M")
        if fixture_datetime >= now_ist - timedelta(hours=2):
            next_ipl_fixture = fixture
            next_ipl_datetime = fixture_datetime
            break

    if next_ipl_fixture:
        fallback = {
            "name": next_ipl_fixture["name"],
            "match_type": "IPL T20",
            "series": "Indian Premier League",
            "venue": next_ipl_fixture["venue"],
            "teams": next_ipl_fixture["teams"],
        }
        fixture_date = next_ipl_datetime
        start_time = fixture_date.strftime("%d %b %Y, %I:%M %p IST")
    else:
        fixture_date = now_ist + timedelta(days=1)
        fixture_date = fixture_date.replace(hour=19, minute=30, second=0, microsecond=0)
        fallback = FALLBACK_FIXTURES[now_ist.toordinal() % len(FALLBACK_FIXTURES)].copy()
        fallback["series"] = "IPL Focus Demo Schedule"
        fallback["match_type"] = "IPL T20"
        start_time = fixture_date.strftime("%d %b %Y, %I:%M %p IST")

    fallback.update(
        {
            "id": f"fallback-{fixture_date.strftime('%Y%m%d')}",
            "status": "Upcoming",
            "start_time": start_time,
            "sort_time": fixture_date.isoformat(),
            "source": "IPL auto-updating fallback schedule",
            "source_url": "https://api.cricapi.com/",
            "note": reason,
            "is_fallback": True,
            "last_updated": now_ist.strftime("%d %b %Y, %I:%M %p IST"),
        }
    )
    return fallback


def extract_match_teams(match):
    if isinstance(match.get("teams"), list) and match["teams"]:
        return [str(team) for team in match["teams"][:2]]
    if match.get("t1") and match.get("t2"):
        return [str(match["t1"]), str(match["t2"])]
    if isinstance(match.get("teamInfo"), list) and len(match["teamInfo"]) >= 2:
        return [str(item.get("name", "")) for item in match["teamInfo"][:2]]

    title = str(match.get("name") or match.get("title") or "")
    separators = [" vs ", " v ", " - "]
    for separator in separators:
        if separator in title:
            parts = [piece.strip() for piece in title.split(separator) if piece.strip()]
            if len(parts) >= 2:
                return parts[:2]
    return []


def normalize_fixture(match):
    teams = extract_match_teams(match)
    start_dt = (
        parse_fixture_datetime(match.get("dateTimeGMT"))
        or parse_fixture_datetime(match.get("date"))
        or parse_fixture_datetime(match.get("matchDate"))
    )
    title = str(match.get("name") or match.get("title") or "Upcoming Match")
    if not title and len(teams) == 2:
        title = f"{teams[0]} vs {teams[1]}"

    return {
        "id": str(match.get("id") or match.get("unique_id") or title.lower().replace(" ", "-")),
        "name": title,
        "match_type": str(match.get("matchType") or match.get("type") or "Cricket"),
        "series": str(match.get("series") or match.get("series_name") or "Featured Fixture"),
        "status": str(match.get("status") or match.get("ms") or "Upcoming"),
        "venue": str(match.get("venue") or match.get("location") or "Venue to be announced"),
        "start_time": format_fixture_datetime(start_dt),
        "sort_time": start_dt.isoformat() if start_dt else "",
        "teams": teams,
    }


def cricket_api_endpoints(api_key):
    query = urlencode({"apikey": api_key, "offset": 0})
    return [
        f"https://api.cricapi.com/v1/matches?{query}",
        f"https://api.cricapi.com/v1/cricScore?{urlencode({'apikey': api_key})}",
        f"https://api.cricapi.com/v1/currentMatches?{query}",
    ]


def fetch_api_matches(api_key):
    matches = []
    errors = []
    for url in cricket_api_endpoints(api_key):
        try:
            with urlopen(url, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {exc}")
            continue

        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, list):
            matches.extend(data)
        elif isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    matches.extend(value)
    return matches, errors


def is_completed_match(status_text):
    status_text = status_text.lower()
    completed_words = [
        "result",
        "won",
        "draw",
        "stumps",
        "complete",
        "completed",
        "finished",
        "abandoned",
        "cancelled",
    ]
    return any(word in status_text for word in completed_words)


def is_ipl_match(fixture):
    searchable = " ".join(
        str(fixture.get(key, ""))
        for key in ["name", "series", "match_type", "status"]
    ).lower()
    teams = " ".join(fixture.get("teams", [])).lower()
    ipl_terms = [
        "ipl",
        "indian premier league",
        "royal challengers",
        "mumbai indians",
        "chennai super kings",
        "kolkata knight riders",
        "sunrisers hyderabad",
        "rajasthan royals",
        "delhi capitals",
        "gujarat titans",
        "lucknow super giants",
        "punjab kings",
    ]
    return any(term in searchable or term in teams for term in ipl_terms)


def fetch_next_match(force_refresh=False):
    cache_key = "cricpredict_next_match"
    if not force_refresh:
        cached_fixture = cache.get(cache_key)
        if cached_fixture:
            return cached_fixture

    api_key = os.getenv("CRICKETDATA_API_KEY", "").strip()
    if not api_key:
        fixture = build_fallback_fixture(
            "Live cricket API key is not configured. IPL-focused fallback is active and automatically picks the next available IPL fixture from the local schedule."
        )
        cache.set(cache_key, fixture, 60 * 10)
        return fixture

    matches, errors = fetch_api_matches(api_key)
    if not matches:
        fixture = build_fallback_fixture(
            "Live cricket API lookup failed or returned no matches. The backend refreshed and switched to the IPL-focused dynamic fallback fixture."
        )
        cache.set(cache_key, fixture, 60 * 10)
        return fixture

    upcoming = []
    now = datetime.utcnow()
    for item in matches:
        normalized = normalize_fixture(item)
        if len(normalized["teams"]) < 2:
            continue
        status_text = normalized["status"].lower()
        if is_completed_match(status_text):
            continue
        start_dt = parse_fixture_datetime(item.get("dateTimeGMT")) or parse_fixture_datetime(item.get("date"))
        if start_dt and start_dt < now - timedelta(hours=2):
            continue
        if not start_dt and "upcoming" not in status_text and "not started" not in status_text and "fixture" not in status_text:
            continue
        sort_key = start_dt or datetime.max
        upcoming.append((sort_key, normalized))

    if not upcoming:
        fixture = build_fallback_fixture(
            "The API refreshed successfully but did not return a future IPL fixture. IPL-focused fallback is being used until a new API fixture is available."
        )
        cache.set(cache_key, fixture, 60 * 10)
        return fixture

    ipl_upcoming = [item for item in upcoming if is_ipl_match(item[1])]
    if ipl_upcoming:
        upcoming = ipl_upcoming
    upcoming.sort(key=lambda item: item[0])
    fixture = upcoming[0][1]
    fixture["source"] = "CricketData API"
    fixture["source_url"] = "https://api.cricapi.com/"
    fixture["note"] = "Fresh upcoming IPL fixture fetched from the configured API. The dashboard refreshes this on login and caches it briefly to avoid unnecessary API calls."
    fixture["is_fallback"] = False
    fixture["last_updated"] = datetime.utcnow().strftime("%d %b %Y, %I:%M %p UTC")
    cache.set(cache_key, fixture, 60 * 15)
    return fixture


def build_match_recommendations(teams):
    batsmen = compute_batsman_predictions(limit=10, teams=teams)
    bowlers = compute_bowler_predictions(limit=10, teams=teams)
    if len(batsmen) < 10:
        batsmen = top_up_players(batsmen, compute_batsman_predictions(limit=25), 10)
    if len(bowlers) < 10:
        bowlers = top_up_players(bowlers, compute_bowler_predictions(limit=25), 10)
    combined = []
    for player in batsmen[:5]:
        combined.append(
            {
                "name": player["name"],
                "team": player["team"],
                "role": "Batter",
                "score": player["score"],
                "detail": player["detail"],
            }
        )
    for player in bowlers[:5]:
        combined.append(
            {
                "name": player["name"],
                "team": player["team"],
                "role": "Bowler",
                "score": player["score"],
                "detail": player["detail"],
            }
        )
    combined.sort(key=lambda item: item["score"], reverse=True)
    return combined, batsmen, bowlers


def index(request):
    user = current_user(request)
    return render(request, "index.html", {"user": user})


def UserLogin(request):
    if current_user(request):
        next_url = request.GET.get("next", "")
        if is_safe_local_path(next_url):
            return redirect(next_url)
        return redirect("Dashboard")
    context = {}
    if request.GET.get("next"):
        add_message(context, "Your session is not active. Login once and we will bring you back to that page.", "warning")
    return render(request, "UserLogin.html", context)


def Register(request):
    if current_user(request):
        return redirect("Dashboard")
    return render(request, "Register.html", {})


@require_http_methods(["POST"])
def Signup(request):
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "").strip()
    contact = request.POST.get("contact", "").strip()
    gender = request.POST.get("gender", "").strip()
    email = request.POST.get("email", "").strip()
    address = request.POST.get("address", "").strip()
    usertype = request.POST.get("usertype", "").strip()

    context = {
        "form_data": {
            "username": username,
            "contact": contact,
            "gender": gender,
            "email": email,
            "address": address,
            "usertype": usertype,
        }
    }

    if not username or not password or not usertype:
        return render(
            request,
            "Register.html",
            add_message(context, "Username, password, and user type are required.", "error"),
        )

    if User.objects.filter(username=username).exists():
        return render(
            request,
            "Register.html",
            add_message(context, f"{username} is already registered. Please choose another username.", "error"),
        )

    User.objects.create(
        username=username,
        password=make_password(password),
        contact_no=contact,
        gender=gender,
        email=email,
        address=address,
        usertype=usertype,
    )
    return render(
        request,
        "UserLogin.html",
        add_message({}, "Account created successfully. Please login to continue.", "success"),
    )


@require_http_methods(["POST"])
def UserLoginAction(request):
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "").strip()

    user = User.objects.filter(username=username).first()
    if not user:
        return render(
            request,
            "UserLogin.html",
            add_message({}, "Login failed. Please check your username and password.", "error"),
        )

    valid_password = False
    if user.password.startswith("pbkdf2_"):
        valid_password = check_password(password, user.password)
    elif user.password == password:
        valid_password = True
        user.password = make_password(password)
        user.save(update_fields=["password"])

    if not valid_password:
        return render(
            request,
            "UserLogin.html",
            add_message({}, "Login failed. Please check your username and password.", "error"),
        )

    request.session["app_user_id"] = user.id
    request.session["app_username"] = user.username
    request.session["fixture_force_refresh"] = True
    request.session.modified = True
    next_url = request.POST.get("next", "").strip()
    if is_safe_local_path(next_url):
        return redirect(next_url)
    return redirect("Dashboard")


@require_login
def Dashboard(request):
    user = current_user(request)
    force_refresh = bool(request.session.pop("fixture_force_refresh", False)) or request.GET.get("refresh") == "1"
    fixture = fetch_next_match(force_refresh=force_refresh)
    match_recommendations, _, _ = build_match_recommendations(fixture["teams"])
    return render(
        request,
        "UserScreen.html",
        {
            "user": user,
            "fixture": fixture,
            "top_recommendations": match_recommendations[:5],
            "force_refresh": force_refresh,
        },
    )


@require_login
def Logout(request):
    request.session.flush()
    return redirect("index")


@require_login
def Batsman(request):
    players = compute_batsman_predictions(limit=15)
    return render(
        request,
        "ViewPrediction.html",
        {
            "user": current_user(request),
            "page_title": "Top 15 Batters",
            "page_subtitle": "Performance rankings built from batting form, efficiency, and model-backed consistency.",
            "players": players,
            "category": "Batter",
            "back_url": reverse("Dashboard"),
            "back_label": "Back to Dashboard",
        },
    )


@require_login
def Ballers(request):
    players = compute_bowler_predictions(limit=15)
    return render(
        request,
        "ViewPrediction.html",
        {
            "user": current_user(request),
            "page_title": "Top 15 Bowlers",
            "page_subtitle": "Performance rankings balanced across wickets, economy, control, and wicket-taking threat.",
            "players": players,
            "category": "Bowler",
            "back_url": reverse("Dashboard"),
            "back_label": "Back to Dashboard",
        },
    )


@require_login
def NextMatchInsights(request):
    fixture = fetch_next_match(force_refresh=request.GET.get("refresh") == "1")
    match_recommendations, batsmen, bowlers = build_match_recommendations(fixture["teams"])
    return render(
        request,
        "NextMatch.html",
        {
            "user": current_user(request),
            "fixture": fixture,
            "top_recommendations": match_recommendations[:10],
            "recommended_batsmen": batsmen[:10],
            "recommended_bowlers": bowlers[:10],
        },
    )
