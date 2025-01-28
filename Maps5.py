from flask import Flask, request, jsonify
import osmnx as ox
import networkx as nx
from scipy.spatial import KDTree
import geopandas as gpd
from shapely.geometry import Point
import numpy as np
from flask_cors import CORS

app = Flask(__name__)

def load_graph(place_name):
    return ox.graph_from_place(place_name, network_type='drive')

def find_nearest_facility(G, place_name, user_location, facility_type):
    tags = {'amenity': facility_type}
    facilities = ox.features_from_place(place_name, tags)

    if facilities.empty:
        return None, None, None

    facilities_projected = facilities.to_crs(epsg=3857)
    facility_coords = [(geom.y, geom.x) for geom in facilities_projected['geometry'].centroid]
    facility_names = facilities['name'].fillna("Unnamed Facility").tolist()

    facility_tree = KDTree(np.array(facility_coords))
    distance, index = facility_tree.query(user_location)

    nearest_facility_name = facility_names[index]
    nearest_facility_coords = facility_coords[index]

    return nearest_facility_name, nearest_facility_coords, distance

def find_shortest_path(G, start, end):
    try:
        path = nx.dijkstra_path(G, source=start, target=end, weight='length')
        length = nx.dijkstra_path_length(G, source=start, target=end, weight='length')
    except nx.NetworkXNoPath:
        return None, None

    return path, length

@app.route('/nearest_facility', methods=['POST'])
def nearest_facility():
    data = request.get_json()
    place_name = data.get('place_name')
    user_location = data.get('user_location')
    facility_type = data.get('facility_type')

    if not place_name or not user_location or not facility_type:
        return jsonify({"error": "Missing required parameters: place_name, user_location, facility_type"}), 400

    try:

        G = load_graph(place_name)

        nearest_name, nearest_coords, nearest_distance = find_nearest_facility(G, place_name, tuple(user_location), facility_type)

        if nearest_name is None:
            return jsonify({"message": f"No facilities of type '{facility_type}' found in {place_name}."}), 404

        response = {
            "nearest_facility": nearest_name,
            "coordinates": nearest_coords,
            "distance_meters": nearest_distance
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/shortest_path', methods=['POST'])
def shortest_path():
    try:
        data = request.get_json()
        place_name = data.get('place_name')
        start_location = data.get('start_location')
        end_location = data.get('end_location')

        if not place_name or not start_location or not end_location:
            return jsonify({"error": "Missing required parameters"}), 400

        G = load_graph(place_name)

        # 获取最近的节点
        start_node = ox.distance.nearest_nodes(G, X=start_location[1], Y=start_location[0])
        end_node = ox.distance.nearest_nodes(G, X=end_location[1], Y=end_location[0])

        # 计算最短路径
        path_nodes = nx.shortest_path(G, start_node, end_node, weight='length')
        path_length = nx.shortest_path_length(G, start_node, end_node, weight='length')

        # 获取路径上每个节点的坐标
        path_coords = []
        for node in path_nodes:
            # 获取节点的坐标
            y = G.nodes[node]['y']  # 纬度
            x = G.nodes[node]['x']  # 经度
            path_coords.append({"lat": y, "lng": x})

        response = {
            "length_meters": path_length,
            "path": path_coords  # 现在返回的是坐标而不是节点ID
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    return response
if __name__ == '__main__':
    app.run(debug=True)
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:3000"],  # 允许的前端域名
            "methods": ["GET", "POST", "OPTIONS"],  # 允许的方法
            "allow_headers": ["Content-Type"]  # 允许的请求头
        }
    })