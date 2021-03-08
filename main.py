# pip install beautifulsoup4
# pip install requests

from bs4 import BeautifulSoup
import requests
import sys

class CarDetail:
    def __init__(self, img_url, name, engine_size, fuel_type, power, max_torque, certification,
            length, width, height, weight, boot_space, urban_cons, extra_cons,
            combined_cons, co2, monthly_cost, fringe_benefit):
        self.img_url, self.name, self.engine_size, self.fuel_type, self.power = img_url, name, engine_size, fuel_type, power
        self.max_torque, self.certification, self.length, self.width = max_torque, certification, length, width
        self.weight, self.boot_space, self.urban_cons, self.extra_cons = weight, boot_space, urban_cons, extra_cons
        self.combined_cons, self.co2, self.monthly_cost, self.fringe_benefit = combined_cons, co2, monthly_cost, fringe_benefit
        # compute total_monthly_price
        # 0.3 is the most common taxable_percentage, so if no co2 is defined i'll use 0.3
        benefit_taxable_percentage = 0.3 if not co2 else 0.5 if float(co2) > 190 else 0.4 if float(co2) > 160 else 0.3 if float(co2) > 60 else 0.25
        monthly_cost_float = float(monthly_cost.replace(",",".") or "0")
        fringe_benefit_float = float(fringe_benefit.replace(",",".") or "0")
        self.benefit_taxable_percentage = str(benefit_taxable_percentage)
        self.total_monthly_price = str(monthly_cost_float + fringe_benefit_float * benefit_taxable_percentage)

    def to_csv_header(self):
        csv_header = ""
        for item in vars(self).items():
            csv_header += item[0] + ","
        return csv_header[:-1]
    def to_csv(self):
        csv = ""
        for item in vars(self).items():
            csv += item[1].replace(",",".") + ","
        return csv[:-1]

def get_brand_urls(session, url):
    brand_urls = []
    page = session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    ul = soup.find("ul", {"class":"brandlist"})
    lis = ul.find_all("li")

    for li in lis:
        brand_urls.append(li.find("a")["href"])

    return brand_urls

def get_car_urls(session, url):
    car_urls = []
    page = session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    models_tables = soup.find_all("div", {"class":"table-modelli"})
    for table in models_tables:
        for td in table.find_all("td", {"class":"al"}):
            car_urls.append(td.find("a")["href"])
        
    return car_urls

def extract_car_feature(car_features, num):
    return car_features[num].find("dd").text.strip().replace("N.D.","")

def scrape_car_detail(session, url, base_url, url_costs):
    page = session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    # picture and name
    img_url = base_url + soup.find("img",{"class":"car_photo_big"})["src"][1:].replace(" ","%20")
    name = soup.find("div",{"class":"breadcrumbs"}).find("li",{"class":"current"}).text.strip()
    # features
    car_features = soup.find("div",{"class":"car_features"}).find_all("dl")
    engine_size = extract_car_feature(car_features,1).split("l")[0][:-1]
    fuel_type = extract_car_feature(car_features,2)
    power = extract_car_feature(car_features,3)[:3]
    max_torque = extract_car_feature(car_features,4)
    certification = extract_car_feature(car_features,5)[:5]
    length = extract_car_feature(car_features,6)[:3]
    width = extract_car_feature(car_features,7)[:3]
    height = extract_car_feature(car_features,8)[:3]
    weight = extract_car_feature(car_features,9)[:4]
    boot_space = extract_car_feature(car_features,12)[:3]
    urban_cons = extract_car_feature(car_features,13)[:3]
    extra_cons = extract_car_feature(car_features,14)[:3]
    combined_cons = extract_car_feature(car_features,15)[:3]
    co2 = extract_car_feature(car_features,17)[:5]
    # costs
    vehicle_id = url.split("/")[-1].split("?")[0]
    pi = url.split("/")[-1].split("?")[1].replace("pi=","")
    costs_page = session.get(url_costs.format(vehicle_id,pi))
    costs_soup = BeautifulSoup(costs_page.content.decode("utf-8"), "html.parser")
    monthly_cost = costs_soup.find_all("dl")[0].find("dd").text.strip()[2:]
    fringe_benefit = costs_soup.find_all("dl")[-1].find("dd").text.strip()[2:]

    return CarDetail(img_url, name, engine_size, fuel_type, power, max_torque, certification,
                     length, width, height, weight, boot_space, urban_cons, extra_cons, 
                     combined_cons, co2, monthly_cost, fringe_benefit)

def write_file(file_name, car_details):
    with open(file_name, "w") as f:
        f.write(car_details[0].to_csv_header() + "\n")
        for detail in car_details:
            f.write(detail.to_csv() + "\n")

def main():
    # check params
    if len(sys.argv) < 3:
        print("specify username and password (e.g. python main.py \"giuseppe.mumolo@avanade.com\" \"mysecretfulpassword\")")
        sys.exit()
    username = sys.argv[1]
    pwd = sys.argv[2]

    # open main page
    car_details = []
    url_auth = "https://www.arval-carconfigurator.com/login/login.do.jsp"
    url_home = "https://www.arval-carconfigurator.com/"
    url_costs = "https://www.arval-carconfigurator.com/inc/quotationVehicleBox.jsp?vehicle_id={}&pi={}"
    data = {"login": username, "password": pwd}

    # login
    s = requests.session()
    s.post(url_auth, data) 
    
    # scrape
    print("scraping home")
    for url_brand in get_brand_urls(s, url_home):
        print(f"scraping brand: {url_brand.split('=')[-1]}")
        for url_car in get_car_urls(s, url_home + url_brand):
            car_details.append(scrape_car_detail(s, url_home + url_car, url_home, url_costs))
    
    # export result to csv
    write_file("cars.csv", car_details)

if __name__ == "__main__":
    main()