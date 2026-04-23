import requests
import folium
import math


# Hàm tính khoảng cách giữa 2 tọa độ (Haversine formula)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c 

# Bước 1: Lấy tọa độ (Nominatim API)
def get_coordinates(city_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": city_name,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "StudentProjectApp/1.0" 
    }
    response = requests.get(url, params=params, headers=headers).json()
    
    if response:
        return float(response[0]["lat"]), float(response[0]["lon"])
    return None, None

# Bước 2: Lấy thời tiết (OpenWeather API)
def get_weather(lat, lon, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric" 
    }
    response = requests.get(url, params=params).json()
    
    if response.get("cod") == 200:
        temp = response["main"]["temp"]
        condition = response["weather"][0]["main"]
        icon = response["weather"][0]["icon"] 
        return temp, condition, icon
    return None, None, None

# Bước 3: Tìm địa điểm gần đó - Công viên (Overpass API)
def get_nearby_parks(lat, lon, radius=20000):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["leisure"="park"](around:{radius}, {lat}, {lon});
      way["leisure"="park"](around:{radius}, {lat}, {lon});
      relation["leisure"="park"](around:{radius}, {lat}, {lon});
    );
    out center;
    """
    headers = {
        "User-Agent": "HCMUS_Student_Project/1.0"
    }
    
    try:
        # Thêm headers vào request
        response = requests.post(url, data={"data": query}, headers=headers)
        
        # Kiểm tra xem server có trả về dữ liệu thành công không (mã 200 là OK)
        if response.status_code != 200:
            print(f"  [!] Lỗi API Overpass (Mã: {response.status_code}). Server có thể đang quá tải.")
            return []
            
        data = response.json()
        
    except Exception as e:
        print(f"  [!] Không thể đọc dữ liệu từ Overpass API: {e}")
        return []

    parks = []
    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "Unnamed Park")
        p_lat = element.get("lat") or element.get("center", {}).get("lat")
        p_lon = element.get("lon") or element.get("center", {}).get("lon")
        
        if p_lat and p_lon:
            distance = calculate_distance(lat, lon, p_lat, p_lon)
            parks.append({
                "name": name,
                "lat": p_lat,
                "lon": p_lon,
                "distance": distance
            })
    return parks

def main():
    OPENWEATHER_API_KEY = "bd5e378503939ddaee76f12ad7a97608" 
    
    city = input("Nhập tên thành phố: ")
    
    #Bước 1
    print("\nĐang lấy tọa độ...")
    lat, lon = get_coordinates(city)
    if not lat:
        print("Không tìm thấy thành phố này.")
        return

    #Bước 2
    print("Đang lấy thông tin thời tiết...")
    temp, condition, icon_code = get_weather(lat, lon, OPENWEATHER_API_KEY)
    
    #Bước 3
    print("Đang tìm công viên lân cận (Bán kính 5km)...")
    parks = get_nearby_parks(lat, lon, radius=5000)

    #Bước 4: Hiển thị kết quả lên console
    print("\n" + "="*30)
    print(f"City: {city.title()}")
    print(f"Coordinates: ({lat:.4f}, {lon:.4f})")
    
    if temp:
        print("Weather:")
        print(f"  - Temperature: {temp}°C")
        print(f"  - Condition: {condition}")
    else:
        print("Không thể lấy thông tin thời tiết. (Kiểm tra lại API Key)")
        
    print("Nearby places (Parks):")
    if not parks:
        print("  Không tìm thấy công viên nào trong bán kính 5km.")
    else:
        for i, park in enumerate(parks, 1):
            print(f"  {i}. {park['name']} (Distance: {park['distance']:.2f} km)")
            
    # Bước 5: Hiển thị kết quả ra bản đồ
    print("\nĐang tạo bản đồ...")
    
    # Khởi tạo bản đồ lấy trung tâm là thành phố
    m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")
    
    # Custom icon thời tiết từ OpenWeather (sử dụng link icon chuẩn của họ)
    weather_icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else ""
    
    # Maker cho trung tâm thành phố (Hiển thị icon thời tiết)
    html_popup = f"<b>{city.title()}</b><br>Temp: {temp}°C<br>Condition: {condition}"
    if weather_icon_url:
        html_popup += f"<br><img src='{weather_icon_url}' width='50' height='50'>"
        
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(html_popup, max_width=200),
        icon=folium.Icon(color="red", icon="info-sign"),
        tooltip="City Center"
    ).add_to(m)
    
    # Marker cho các công viên và vẽ đường thẳng từ tâm đến công viên
    for park in parks:
        # Marker cho công viên
        folium.Marker(
            [park['lat'], park['lon']],
            popup=f"<b>{park['name']}</b><br>Distance: {park['distance']:.2f} km",
            icon=folium.Icon(color="green", icon="tree", prefix='fa'),
            tooltip=park['name']
        ).add_to(m)
        
        # Vẽ đường (PolyLine) nối từ trung tâm đến công viên
        folium.PolyLine(
            locations=[[lat, lon], [park['lat'], park['lon']]],
            color="blue",
            weight=2,
            opacity=0.6,
            tooltip=f"{park['distance']:.2f} km"
        ).add_to(m)

    map_filename = f"{city.replace(' ', '_').lower()}_map.html"
    m.save(map_filename)
    print(f"✅ Đã tạo bản đồ thành công: Lưu tại file '{map_filename}'")
    print("Bạn có thể mở file HTML này bằng trình duyệt (Chrome/Edge/Safari) để xem kết quả.")

if __name__ == "__main__":
    main()