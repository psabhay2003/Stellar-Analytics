# -*- coding: utf-8 -*-
"""Stellar Analytics.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/13CRntOvLXsn1uBk9v9EjQL_w80R7x5Q8
"""

#This Colab Notebook aims to create a machine learning model for classifying exoplanets into three classes using a custom "Habitability Index."

# Commented out IPython magic to ensure Python compatibility.
#Importing the libraries to be used during the process
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# %matplotlib inline
import seaborn as sns
from sklearn.preprocessing import RobustScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

#loading the dataset
df = pd.read_csv("https://raw.githubusercontent.com/psabhay2003/Stellar-Analytics/refs/heads/main/exoplanet_dataset.csv")
df.head()

#exploring the dataset
df.info()
df.shape
df.isnull().sum()
df.describe()

#data cleaning and pre-processing

#dropping unnecessary columns
#firstly dropping columns with similar data but in different form
columns_to_drop_1 = ["S_RA_STR", "S_RA_TXT", "S_DEC_STR", "S_DEC_TXT", "S_CONSTELLATION_ABR", "S_CONSTELLATION_ENG"]
#secondly dropping columns with data irrevelant to habitability
columns_to_drop_2 = ["P_DETECTION", "P_DISCOVERY_FACILITY", "P_YEAR", "P_UPDATE", "P_MASS_ORIGIN", "S_NAME_HD", "S_NAME_HIP", "S_CONSTELLATION", "P_OMEGA"]
# df_cleaned = df.drop(columns=columns_to_drop_1 + columns_to_drop_2, axis=1, inplace=True) # inplace=True was causing the issue
df_cleaned = df.drop(columns=columns_to_drop_1 + columns_to_drop_2, axis=1) # Assign the result to df_cleaned
#check whether the columns were dropped
print(df_cleaned.columns) # Print columns of df_cleaned

#filling missing values with median for numerical features
#firstly we have to separate numeric and non-numeric fields otherwise it will give TypeError
numeric_cols = df_cleaned.select_dtypes(include=['number']).columns
non_numeric_cols = df_cleaned.select_dtypes(exclude=['number']).columns
df_cleaned[numeric_cols] = df_cleaned[numeric_cols].fillna(df_cleaned[numeric_cols].median())
#filling missing non-numeric values with mode
df_cleaned[non_numeric_cols] = df_cleaned[non_numeric_cols].apply(lambda x: x.fillna(x.mode()[0]))

#verifying whether missing values are handled or not
print(df_cleaned.isnull().sum())

#Outlier Handeling and Normalisation
outlier_features = df_cleaned.select_dtypes(include=np.number).columns
# Boxplot for Outliers
plt.figure(figsize=(12, 6))
sns.boxplot(data=df_cleaned[outlier_features])
plt.title("Boxplot Showing Outliers in Features")
plt.xticks(rotation=45)
plt.show()

# Remove outliers using the IQR method
for col in outlier_features:
    Q1 = df_cleaned[col].quantile(0.25)
    Q3 = df_cleaned[col].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df_cleaned = df_cleaned[(df_cleaned[col] >= lower_bound) & (df_cleaned[col] <= upper_bound)]

# Plot the boxplot AFTER outlier removal
plt.figure(figsize=(12, 6))
sns.boxplot(data=df_cleaned[outlier_features])
plt.title("Boxplot After Outlier Removal")
plt.xticks(rotation=45)
plt.show()

# Normalization: Normalize all numeric features using RobustScaler
#Since many astrophysical features (e.g., mass, period) span several orders of magnitude and can be skewed even after outlier removal, using a RobustScaler—can be beneficial.
#It minimizes the influence of any remaining extreme values.
scaler = RobustScaler()
df_normalized = df_cleaned.copy()
df_normalized[numeric_cols] = scaler.fit_transform(df_cleaned[numeric_cols])

# Optional: Visualize the correlation matrix after normalization
plt.figure(figsize=(15, 12))
corr_matrix = df_normalized[numeric_cols].corr()
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm')
plt.title("Correlation Matrix After Normalization")
plt.show()

#According to Pearson Correlation, the diagonal line represents perfect correlation of a feature with itself(correlation=1)
#Strong Positive Correlation(+1): When one feature increases, the other also increases
#Strong Negative Correlation(-1): When one feature decreases, the other tends to decrease
#No Correlation(0): No relationship between features
#Based on the above correlation matrix:
#P_MASS and P_POTENTIAL are strong positively correlated(0.98)
#P_ESCAPE and P_POTENTIAL are strong positively correlated(1)
#S_TEMPERATURE, S_MASS, and S_RADIUS are strong positively correlated(0.95)
#P_SEMI_MAJOR_AXIS, P_HILL_SPHERE, P_DISTANCE, P_PERIASTRON, P_APASTRON, P_DISTANCE_EFF are strong positively correlated(0.97-1)
#S_LOG_G, S_LOG_LUM, S_SNOW_LINE, S_RADIUS are strong negatively correlated(-0.7)

#dropping highly correlated fields, keeping important fields undropped
columns_to_drop_3 = ["P_HILL_SPHERE", "P_PERIASTRON", "P_APASTRON", "P_DISTANCE_EFF", "S_TEMPERATURE", "P_POTENTIAL"]
df_cleaned.drop(columns=columns_to_drop_3, axis=1, inplace=True)
#check whether the columns were dropped
print(df_cleaned.columns)

#FEATURE ENGINEERING: To derive new features by developing relations between the existing features
#Earth Similarity Index(ESI):
#The Earth Similarity Index (ESI) is a scale to physically compare other planets to Earth. The scale is between 0 (no similarity to Earth) and 1 (Earth-like). Planets with an ESI between 0.8 and 1.0 are more likely to be similar to Earth.
#Feature Engineering: To derive new features by developing relations between the existing features
#Earth Similarity Index(ESI):
#The Earth Similarity Index (ESI) is a scale to physically compare other planets to Earth. The scale is between 0 (no similarity to Earth) and 1 (Earth-like). Planets with an ESI between 0.8 and 1.0 are more likely to be similar to Earth.
#ESI helps identify planets with Earth-like physical properties, which is a strong indicator of potential habitability.
# Earth constants for comparison
EARTH_FLUX = 1.0 #Stellar Flux is calculated relative to Earth
EARTH_RADIUS = 1.0 #Planetary Radius is also relative to Earth

import math

def calculate_esi(row):
    S = row['P_FLUX']
    R = row['P_RADIUS']

#Calculating the similarity terms for flux and radius
    term_S = (S - EARTH_FLUX) / (S + EARTH_FLUX)
    term_R = (R - EARTH_RADIUS) / (R + EARTH_RADIUS)

#Computing the combined value (averaging the squared differences)
    value = 0.5 * (term_S**2 + term_R**2)

#ESI is defined as 1 minus the square root of the above value
    ESI = 1 - math.sqrt(value)
    return ESI
df_cleaned['ESI'] = df_cleaned.apply(calculate_esi, axis=1)
print(df_cleaned['ESI'])

# Long-Term Stability
#This feature highlights planets with minimal extreme climate variations, increasing the likelihood of sustaining life long-term.
#Higher Stability: Values > 0.5 indicate stable orbits, favorable for maintaining consistent climates.
#Moderate Stability: (0.3-0.5) indicate some climate variability, but still potentially habitable.
#Low Stability: Values < 0.3 indicate unstable orbits, extreme temperature swings, or potential ejection from the habitable zone
def calculate_stability(row):
    eccentricity = row['P_ECCENTRICITY']
    stellar_age = row['S_AGE']
    semi_major_axis = row['P_SEMI_MAJOR_AXIS']

    stability = (1 - eccentricity) * np.log1p(stellar_age) / (1 + semi_major_axis)
    return stability
df_cleaned['Long_Term_Stability'] = df_cleaned.apply(calculate_stability, axis=1)
print(df_cleaned['Long_Term_Stability'])

#Star-Planet Energy Flux Ratio
#To measure how much energy a planet receives from its star.
#The amount of radiation received from the host star directly impacts habitability.
def calculate_flux_ratio(row):
    L_star = row['S_LUMINOSITY']
    F_planet = row['P_FLUX']
    d = row['P_SEMI_MAJOR_AXIS']

    Flux_Ratio = ((F_planet * 4 * np.pi *d ** 2)/(L_star))
    return Flux_Ratio
df_cleaned['Flux Ratio'] = df_cleaned.apply(calculate_flux_ratio, axis=1)
print(df_cleaned['Flux Ratio'])

#Habitability Zone Distance(HZD)
#To measure how close a planet is to the ideal habitable zone.
#A planet that’s too far or too close to its star might not be habitable.
#Negative values = Planet is inside the habitable zone
#Positive values = Planet is too far out
#Very negative values = Planet is too close to the star
def habitable_zone_distance(row):
    HZ_inner = 0.75 * row['S_LUMINOSITY'] ** 0.5  # Conservative inner edge
    HZ_outer = 1.77 * row['S_LUMINOSITY'] ** 0.5  # Conservative outer edge
    HZ_center = (HZ_inner + HZ_outer) / 2
    HZ_width = HZ_outer - HZ_inner
    return (row['P_SEMI_MAJOR_AXIS'] - HZ_center) / HZ_width

df_cleaned['HZD'] = df_cleaned.apply(habitable_zone_distance, axis=1)
print(df_cleaned['HZD'])

#Escape Velocity Ratio
#To measure the ratio of escape velocity of planet relative to Earth's escape velocity
#The planets with value close to 1 will have almost same Escape Velocity as of Earth
EARTH_ESCAPE_VELOCITY = 11.2  # in km/s
df_cleaned['Escape_Velocity_Ratio'] = df_cleaned['P_ESCAPE'] / EARTH_ESCAPE_VELOCITY
print(df_cleaned['Escape_Velocity_Ratio'])

#Tidal Force Ratio
#The Tidal Force Ratio of Earth to Sun is 1:2 = 0.5, any value close to it, indicates strong correlation with Earth and similar habitability
def calculate_tidal_force(row):
    Mp = row['P_MASS']
    Rp = row['P_RADIUS']
    Ms = row['S_MASS']
    d = row['P_SEMI_MAJOR_AXIS']

    Tidal_Force_Ratio = ((Mp/Ms) * (Rp/d ** 3))/0.5
    return Tidal_Force_Ratio
df_cleaned['Tidal_Force_Ratio'] = df_cleaned.apply(calculate_tidal_force, axis=1)
print(df_cleaned['Tidal_Force_Ratio'])

# Create a scaler instance
scaler = MinMaxScaler()

# Normalize the Tidal_Force_Ratio column
df_cleaned['Tidal_Force_Ratio_Norm'] = scaler.fit_transform(df_cleaned[['Tidal_Force_Ratio']])

# Display the original and normalized values
print(df_cleaned['Tidal_Force_Ratio_Norm'].head())

#Defining a custom Habitability class using rule-based decision tree
def classify_habitability_rule(row):
    score = 0

    # ESI (output ranges from 0.25 to 0.35)
    if row['ESI'] >= 0.35:
        score += 2
    elif row['ESI'] >= 0.25:
        score += 1

    # Long-Term Stability ( output ranges from 1.0 to 1.5, with most values near to 1)
    if row['Long_Term_Stability'] >= 1.2:
        score += 2
    elif row['Long_Term_Stability'] >= 1.0:
        score += 1

    # Habitability Zone Distance (HZD, ideal near -1.0)
    if -1.2 <= row['HZD'] <= -0.8:
        score += 2
    elif (-1.5 <= row['HZD'] < -1.2) or (-0.8 < row['HZD'] <= -0.5):
        score += 1

    # Flux Ratio (ideal near 12.57)
    if abs(row['Flux Ratio'] - 12.57) <= 1:
        score += 2
    elif abs(row['Flux Ratio'] - 12.57) <= 2:
        score += 1

    # Escape Velocity Ratio (output ranges from 0.12 to 0.15)
    if row['Escape_Velocity_Ratio'] >= 0.15:
        score += 2
    elif row['Escape_Velocity_Ratio'] >= 0.12:
        score += 1

    # Tidal Force Ratio (ideal if between 0.8 and 1.2)
    if 0.8 <= row['Tidal_Force_Ratio'] <= 1.2:
        score += 2
    elif (0.5 <= row['Tidal_Force_Ratio'] < 0.8) or (1.2 < row['Tidal_Force_Ratio'] <= 1.5):
        score += 1

    # Determine class based on total score (max value is 12)
    if score >= 9:
        return "Potentially Habitable"
    elif score >= 6:
        return "Marginally Habitable"
    else:
        return "Non-Habitable"

# Applying the rule-based classification
df_cleaned['Habitability_Class'] = df_cleaned.apply(classify_habitability_rule, axis=1)

# Selecting features derived in feature engineering
features = ['ESI', 'Long_Term_Stability', 'HZD', 'Flux Ratio', 'Escape_Velocity_Ratio', 'Tidal_Force_Ratio']
X = df_cleaned[features]
y = df_cleaned['Habitability_Class']

# Spliting the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=42, stratify=y)
#I increased the test size to classify more planets using the model, it can vary from 20% to 40%
# Train Decision Tree Classifier
dt_model = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
dt_model.fit(X_train, y_train)

# Make predictions and evaluate the model
y_pred = dt_model.predict(X_test)
# Compute evaluation metrics
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average="weighted")
recall = recall_score(y_test, y_pred, average="weighted")
f1 = f1_score(y_test, y_pred, average="weighted")
conf_matrix = confusion_matrix(y_test, y_pred)
report = classification_report(y_test, y_pred)
# Print results
print("Accuracy:", accuracy)
print("Precision:", precision)
print("Recall:", recall)
print("F1 Score:", f1)
print("Confusion Matrix:\n", conf_matrix)
print("Classification Report:\n", report)
# Visualizing feature relations
plt.figure(figsize=(10, 6))
sns.pairplot(df_cleaned, vars=['ESI',  'Long_Term_Stability', 'HZD', 'Escape_Velocity_Ratio', 'Tidal_Force_Ratio'], hue="Habitability_Class")
plt.show()
#It can be interpreted that there is an imbalance in classes as the model predicts most of the exoplanets as Marginally Habitable, this is true in real-world case as well because discovering a potentially habitable planet is difficult.
#A potentially habitable planet is the one with astronomical features similar to Earth which is rare to occur.
#Therefore, model is correct in classifying most of the planets as marginally habitable.