import streamlit as st
import json
import geopandas as gpd
import pandas as pd
from io import StringIO
import jsonschema
from jsonschema import validate
import os

# Set page title and configuration
st.set_page_config(page_title="GeoJSON Comparison Tool", layout="wide")
st.title("GeoJSON Comparison Tool")

# Function to check GeoJSON validity
def validate_geojson(data):
    """Validate if the provided data conforms to GeoJSON schema"""
    try:
        # Basic GeoJSON schema
        geojson_schema = {
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {"type": "string", "enum": ["FeatureCollection", "Feature", "Point", "LineString", "Polygon", 
                                                  "MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"]},
                "features": {"type": "array"},
                "geometry": {"type": "object"},
                "properties": {"type": "object"},
                "coordinates": {"type": "array"}
            }
        }
        
        validate(instance=data, schema=geojson_schema)
        
        # Further validation for specific types
        if data.get("type") == "FeatureCollection" and "features" not in data:
            return False, "FeatureCollection must have 'features' array"
        
        if data.get("type") == "Feature" and "geometry" not in data:
            return False, "Feature must have 'geometry' property"
            
        return True, "Valid GeoJSON"
    except jsonschema.exceptions.ValidationError as e:
        return False, f"Invalid GeoJSON: {e.message}"
    except Exception as e:
        return False, f"Error during validation: {str(e)}"

# Function to analyze GeoJSON structure
def analyze_geojson(data):
    """Analyze the structure of a GeoJSON file"""
    analysis = {}
    
    # Determine the GeoJSON type
    analysis["type"] = data.get("type", "Unknown")
    
    # Count features if it's a FeatureCollection
    if analysis["type"] == "FeatureCollection":
        features = data.get("features", [])
        analysis["feature_count"] = len(features)
        
        # Feature types
        feature_types = {}
        property_keys = set()
        
        for feature in features:
            geo_type = feature.get("geometry", {}).get("type", "Unknown")
            feature_types[geo_type] = feature_types.get(geo_type, 0) + 1
            
            # Collect property keys
            if "properties" in feature and feature["properties"]:
                property_keys.update(feature["properties"].keys())
        
        analysis["geometry_types"] = feature_types
        analysis["property_keys"] = list(property_keys)
    
    # For single feature
    elif analysis["type"] == "Feature":
        geo_type = data.get("geometry", {}).get("type", "Unknown")
        analysis["geometry_type"] = geo_type
        
        if "properties" in data and data["properties"]:
            analysis["property_keys"] = list(data["properties"].keys())
    
    # For direct geometry
    elif analysis["type"] in ["Point", "LineString", "Polygon", "MultiPoint", 
                             "MultiLineString", "MultiPolygon", "GeometryCollection"]:
        analysis["geometry_type"] = analysis["type"]
    
    return analysis

# Function to find differences between two GeoJSON files
def compare_geojson(geojson1, geojson2):
    """Compare two GeoJSON files and identify differences"""
    differences = {}
    
    # Compare types
    differences["different_types"] = geojson1.get("type") != geojson2.get("type")
    
    # Compare feature counts if they are FeatureCollections
    if geojson1.get("type") == "FeatureCollection" and geojson2.get("type") == "FeatureCollection":
        features1 = geojson1.get("features", [])
        features2 = geojson2.get("features", [])
        
        differences["feature_count_1"] = len(features1)
        differences["feature_count_2"] = len(features2)
        differences["feature_count_diff"] = len(features1) - len(features2)
        
        # Compare property keys
        keys1 = set()
        keys2 = set()
        
        for feature in features1:
            if "properties" in feature and feature["properties"]:
                keys1.update(feature["properties"].keys())
        
        for feature in features2:
            if "properties" in feature and feature["properties"]:
                keys2.update(feature["properties"].keys())
        
        differences["unique_keys_1"] = list(keys1 - keys2)
        differences["unique_keys_2"] = list(keys2 - keys1)
        differences["common_keys"] = list(keys1.intersection(keys2))
    
    return differences

# Create two columns for file uploads
col1, col2 = st.columns(2)

with col1:
    st.header("GeoJSON File 1")
    file1 = st.file_uploader("Upload first GeoJSON file", type=["json", "geojson"])
    sample_data1 = st.checkbox("Use sample data for File 1")

with col2:
    st.header("GeoJSON File 2")
    file2 = st.file_uploader("Upload second GeoJSON file", type=["json", "geojson"])
    sample_data2 = st.checkbox("Use sample data for File 2")

# Sample GeoJSON data
sample_geojson1 = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Point 1", "value": 42},
            "geometry": {
                "type": "Point",
                "coordinates": [0, 0]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Line 1", "length": 10.5},
            "geometry": {
                "type": "LineString",
                "coordinates": [[0, 0], [1, 1]]
            }
        }
    ]
}

sample_geojson2 = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Point A", "elevation": 100},
            "geometry": {
                "type": "Point",
                "coordinates": [2, 2]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Polygon A", "area": 25.0},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]]
            }
        }
    ]
}

# Process GeoJSON files
geojson_data1 = None
geojson_data2 = None

if file1 is not None:
    try:
        content1 = file1.getvalue().decode("utf-8")
        geojson_data1 = json.loads(content1)
    except Exception as e:
        st.error(f"Error reading file 1: {str(e)}")
elif sample_data1:
    geojson_data1 = sample_geojson1

if file2 is not None:
    try:
        content2 = file2.getvalue().decode("utf-8")
        geojson_data2 = json.loads(content2)
    except Exception as e:
        st.error(f"Error reading file 2: {str(e)}")
elif sample_data2:
    geojson_data2 = sample_geojson2

# Display analysis if both files are loaded
if geojson_data1 is not None or geojson_data2 is not None:
    st.divider()
    
    # Analysis columns
    col1, col2 = st.columns(2)
    
    with col1:
        if geojson_data1 is not None:
            st.subheader("GeoJSON 1 Analysis")
            
            # Check validity
            valid1, message1 = validate_geojson(geojson_data1)
            if valid1:
                st.success("✅ Valid GeoJSON structure")
            else:
                st.error(f"❌ Invalid GeoJSON: {message1}")
            
            # Show analysis
            analysis1 = analyze_geojson(geojson_data1)
            
            st.write("**Type:**", analysis1.get("type", "Unknown"))
            
            if "feature_count" in analysis1:
                st.write("**Feature Count:**", analysis1["feature_count"])
            
            if "geometry_types" in analysis1:
                st.write("**Geometry Types:**")
                for geo_type, count in analysis1["geometry_types"].items():
                    st.write(f"- {geo_type}: {count} features")
            
            if "geometry_type" in analysis1:
                st.write("**Geometry Type:**", analysis1["geometry_type"])
            
            if "property_keys" in analysis1:
                st.write("**Property Keys:**")
                st.write(", ".join(analysis1["property_keys"]))
            
            # Show raw data
            with st.expander("View Raw GeoJSON 1"):
                st.json(geojson_data1)
    
    with col2:
        if geojson_data2 is not None:
            st.subheader("GeoJSON 2 Analysis")
            
            # Check validity
            valid2, message2 = validate_geojson(geojson_data2)
            if valid2:
                st.success("✅ Valid GeoJSON structure")
            else:
                st.error(f"❌ Invalid GeoJSON: {message2}")
            
            # Show analysis
            analysis2 = analyze_geojson(geojson_data2)
            
            st.write("**Type:**", analysis2.get("type", "Unknown"))
            
            if "feature_count" in analysis2:
                st.write("**Feature Count:**", analysis2["feature_count"])
            
            if "geometry_types" in analysis2:
                st.write("**Geometry Types:**")
                for geo_type, count in analysis2["geometry_types"].items():
                    st.write(f"- {geo_type}: {count} features")
            
            if "geometry_type" in analysis2:
                st.write("**Geometry Type:**", analysis2["geometry_type"])
            
            if "property_keys" in analysis2:
                st.write("**Property Keys:**")
                st.write(", ".join(analysis2["property_keys"]))
            
            # Show raw data
            with st.expander("View Raw GeoJSON 2"):
                st.json(geojson_data2)

    # Comparison section
    if geojson_data1 is not None and geojson_data2 is not None:
        st.divider()
        st.header("GeoJSON Comparison")
        
        # Compare the two GeoJSON files
        comparison = compare_geojson(geojson_data1, geojson_data2)
        
        # Display comparison results
        if comparison["different_types"]:
            st.warning(f"⚠️ Different GeoJSON types: {geojson_data1.get('type')} vs {geojson_data2.get('type')}")
        else:
            st.success(f"✅ Same GeoJSON type: {geojson_data1.get('type')}")
        
        if "feature_count_diff" in comparison:
            if comparison["feature_count_diff"] == 0:
                st.success(f"✅ Same feature count: {comparison['feature_count_1']} features")
            else:
                st.warning(f"⚠️ Different feature counts: {comparison['feature_count_1']} vs {comparison['feature_count_2']} (difference: {abs(comparison['feature_count_diff'])})")
        
        # Display property key differences
        if "common_keys" in comparison:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Unique Keys in GeoJSON 1")
                if comparison["unique_keys_1"]:
                    for key in comparison["unique_keys_1"]:
                        st.write(f"- {key}")
                else:
                    st.write("None")
            
            with col2:
                st.subheader("Common Keys")
                if comparison["common_keys"]:
                    for key in comparison["common_keys"]:
                        st.write(f"- {key}")
                else:
                    st.write("None")
            
            with col3:
                st.subheader("Unique Keys in GeoJSON 2")
                if comparison["unique_keys_2"]:
                    for key in comparison["unique_keys_2"]:
                        st.write(f"- {key}")
                else:
                    st.write("None")
        
        # Try to visualize if we have valid GeoJSON
        if (valid1 if geojson_data1 is not None else False) and (valid2 if geojson_data2 is not None else False):
            st.divider()
            st.header("GeoJSON Visualization")
            
            try:
                # Convert JSON to GeoDataFrames
                if geojson_data1 is not None:
                    gdf1 = gpd.GeoDataFrame.from_features(
                        geojson_data1["features"] if geojson_data1.get("type") == "FeatureCollection" 
                        else [geojson_data1] if geojson_data1.get("type") == "Feature"
                        else []
                    )
                    
                if geojson_data2 is not None:
                    gdf2 = gpd.GeoDataFrame.from_features(
                        geojson_data2["features"] if geojson_data2.get("type") == "FeatureCollection" 
                        else [geojson_data2] if geojson_data2.get("type") == "Feature"
                        else []
                    )
                
                # Basic visualization placeholder
                st.write("Visualization would go here in a complete app.")
                st.write("This would typically use Folium, MapboxGL, or a similar mapping library.")
                
            except Exception as e:
                st.error(f"Error visualizing GeoJSON: {str(e)}")
                st.write("Could not visualize the GeoJSON files, but analysis is still available above.")
