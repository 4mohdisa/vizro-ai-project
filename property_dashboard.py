import pandas as pd
import random
from datetime import datetime, timedelta
from vizro_ai import VizroAI
from vizro import Vizro
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
import vizro.models as vm
import vizro.plotly.express as px
import socket  # Added for port checking

# Load environment variables
load_dotenv()

# Function to generate more realistic fake property data
def generate_property_data(num_records=250):
    # More varied property types with weighted distribution
    property_types = {
        "House": 0.35, 
        "Apartment": 0.25, 
        "Townhouse": 0.15, 
        "Condo": 0.15, 
        "Villa": 0.10
    }
    
    # More varied statuses with weighted distribution
    statuses = {
        "Sold": 0.4, 
        "Listed": 0.3, 
        "Under Contract": 0.2, 
        "Pending": 0.1
    }
    
    # More agent names
    agent_names = [
        "John Smith", "Sarah Johnson", "Michael Brown", "Emma Davis", 
        "David Wilson", "Lisa Moore", "Robert Taylor", "Jennifer Anderson",
        "Thomas White", "Jessica Martinez", "Daniel Thompson", "Olivia Garcia",
        "William Rodriguez", "Sophia Lee", "James Harris", "Emily Clark"
    ]
    
    # More realistic locations with neighborhoods
    locations = {
        "Downtown": ["Central District", "Harbor View", "Financial Quarter"],
        "Uptown": ["North Hills", "Parkside", "University Area"],
        "Westside": ["Sunset", "Ocean View", "Golden Gate"],
        "Eastside": ["Riverside", "Lakefront", "Highland Park"],
        "Suburbs": ["Greenfield", "Pleasant Valley", "Oak Ridge"]
    }
    
    # Price ranges by property type (min, max, mean, std)
    price_ranges = {
        "House": (400000, 1500000, 750000, 250000),
        "Apartment": (250000, 800000, 450000, 150000),
        "Townhouse": (350000, 1000000, 600000, 150000),
        "Condo": (300000, 900000, 550000, 120000),
        "Villa": (600000, 2500000, 1200000, 400000)
    }
    
    # Square meter ranges by property type (min, max)
    sqm_ranges = {
        "House": (120, 350),
        "Apartment": (60, 150),
        "Townhouse": (90, 200),
        "Condo": (70, 180),
        "Villa": (200, 500)
    }
    
    # Bedroom and bathroom ranges by property type
    room_ranges = {
        "House": {"beds": (2, 6), "baths": (1, 4)},
        "Apartment": {"beds": (1, 3), "baths": (1, 2)},
        "Townhouse": {"beds": (2, 4), "baths": (1, 3)},
        "Condo": {"beds": (1, 3), "baths": (1, 2)},
        "Villa": {"beds": (3, 6), "baths": (2, 5)}
    }
    
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)
    
    # Generate data with more realistic patterns
    data = []
    for _ in range(num_records):
        # Select property type based on weighted distribution
        property_type = random.choices(
            list(property_types.keys()), 
            weights=list(property_types.values()), 
            k=1
        )[0]
        
        # Select status based on weighted distribution
        status = random.choices(
            list(statuses.keys()), 
            weights=list(statuses.values()), 
            k=1
        )[0]
        
        # Generate listing date with more recent dates being more common
        days_ago = int(random.triangular(0, 365, 90))  # More listings in recent months
        listing_date = today - timedelta(days=days_ago)
        
        # Generate sale date only for sold properties
        # Time to sell is shorter for desirable properties
        if status == "Sold":
            # Houses and villas sell faster in this simulation
            if property_type in ["House", "Villa"]:
                sell_days = random.randint(10, 60)
            else:
                sell_days = random.randint(20, 90)
            sale_date = listing_date + timedelta(days=sell_days)
            if sale_date > today:  # Ensure sale date isn't in the future
                sale_date = today - timedelta(days=random.randint(1, 10))
        else:
            sale_date = None
        
        # Select location with district/neighborhood
        area = random.choice(list(locations.keys()))
        neighborhood = random.choice(locations[area])
        location = f"{area} - {neighborhood}"
        
        # Generate price based on property type with normal distribution
        min_price, max_price, mean_price, std_price = price_ranges[property_type]
        price = int(random.normalvariate(mean_price, std_price))
        price = max(min_price, min(max_price, price))  # Clamp to range
        
        # Generate square meters based on property type
        min_sqm, max_sqm = sqm_ranges[property_type]
        square_meters = random.randint(min_sqm, max_sqm)
        
        # Generate bedrooms and bathrooms based on property type
        min_beds, max_beds = room_ranges[property_type]["beds"]
        min_baths, max_baths = room_ranges[property_type]["baths"]
        bedrooms = random.randint(min_beds, max_beds)
        bathrooms = random.randint(min_baths, max_baths)
        
        # Add the property to our dataset
        data.append({
            "property_type": property_type,
            "price": price,
            "status": status,
            "agent_name": random.choice(agent_names),
            "listing_date": listing_date,
            "sale_date": sale_date,
            "location": location,
            "area": area,  # Adding area as a separate column for filtering
            "neighborhood": neighborhood,  # Adding neighborhood for more detail
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "square_meters": square_meters,
            "price_per_sqm": round(price / square_meters, 2)  # Adding derived metric
        })
    
    return pd.DataFrame(data)

# Function to find an available port
def find_available_port(start_port=8091, max_attempts=10):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return start_port + max_attempts  # If all ports are busy, return the last one

# Generate data
print("Generating property data...")
df = generate_property_data(100)
print(f"Generated {len(df)} property records.")

# Save CSV
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "property_data.csv")
df.to_csv(csv_path, index=False)
print(f"Saved property data to: {csv_path}")

# Prompt to generate dashboard
user_prompt = """
Create a one-page dashboard with:
1. Bar chart: Number of properties sold by property type
2. Box plot: Distribution of prices by property type
3. Line chart: Number of listings over time based on listing_date
4. Table: All property listings
5. Filters: status, agent_name, property_type, location
6. Price range slider
Use a clean layout.
"""

# Try Vizro-AI dashboard generation
try:
    print("Attempting AI-generated dashboard...")
    vizro_ai = VizroAI(model="gpt-4o")
    # Commented out to avoid errors - uncomment if you want to try AI generation
    # dashboard = vizro_ai.dashboard([df], user_prompt)
    # Vizro().build(dashboard).run(port=8090)
except Exception as e:
    print(f"\n⚠️ Vizro-AI dashboard generation failed:\n{e}")
    print("Falling back to manual dashboard creation...")

# Create a more organized dashboard with improved layout and grid system
fallback_dashboard = vm.Dashboard(
    title="Real Estate Market Analytics",
    pages=[
        # First page - Market Overview with key metrics
        vm.Page(
            title="Market Overview",
            components=[
                # Row 1: Distribution charts (side by side)
                vm.Graph(
                    id="pie_chart", 
                    title="Properties by Type",
                    figure=px.pie(
                        df, names="property_type", 
                        color="property_type",
                        hole=0.3,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    ).update_layout(
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=350
                    )
                ),
                vm.Graph(
                    id="bar_chart", 
                    title="Properties by Status",
                    figure=px.bar(
                        df.groupby("status").size().reset_index(name="count"),
                        x="status", y="count",
                        color="status",
                        text="count",
                        color_discrete_sequence=px.colors.qualitative.Bold
                    ).update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=350
                    )
                ),
                
                # Row 2: Price analysis charts (side by side)
                vm.Graph(
                    id="price_by_type", 
                    title="Average Price by Property Type",
                    figure=px.bar(
                        df.groupby("property_type")["price"].mean().reset_index(),
                        x="property_type", y="price",
                        color="property_type",
                        text_auto='.2s',
                        labels={"price": "Average Price ($)", "property_type": "Property Type"},
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    ).update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=350
                    )
                ),
                vm.Graph(
                    id="price_by_area", 
                    title="Price Distribution by Area",
                    figure=px.box(
                        df, x="area", y="price",
                        color="area",
                        labels={"price": "Price ($)", "area": "Area"},
                        color_discrete_sequence=px.colors.qualitative.Bold
                    ).update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=350
                    )
                ),
                
                # Row 3: Time series analysis (full width)
                vm.Graph(
                    id="time_series", 
                    title="Listings Over Time",
                    figure=px.line(
                        df.groupby(df['listing_date'].dt.to_period('M').dt.to_timestamp()).size().reset_index(name='count'),
                        x='listing_date', y='count',
                        labels={"listing_date": "Month", "count": "Number of Listings"},
                        markers=True,
                        line_shape="spline"
                    ).update_traces(
                        line=dict(width=3)
                    ).update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=350
                    )
                )
            ],
            controls=[
                vm.Filter(column="property_type"),
                vm.Filter(column="status"),
                vm.Filter(column="area"),
                vm.Filter(column="agent_name")
            ]
        ),
        
        # Second page - Detailed Analysis with more complex visualizations
        vm.Page(
            title="Detailed Analysis",
            components=[
                # Interactive scatter plot (full width)
                vm.Graph(
                    id="property_scatter", 
                    title="Property Price vs. Size",
                    figure=px.scatter(
                        df, x="square_meters", y="price", 
                        color="property_type",
                        size="bedrooms",
                        hover_data=["agent_name", "location", "bedrooms", "bathrooms", "price_per_sqm", "status"],
                        labels={"square_meters": "Size (sq. meters)", "price": "Price ($)"},
                        opacity=0.7,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    ).update_layout(
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=400
                    )
                ),
                
                # Price heatmap by area and property type
                vm.Graph(
                    id="price_heatmap", 
                    title="Average Price Heatmap",
                    figure=px.density_heatmap(
                        df, x="property_type", y="area", z="price", 
                        histfunc="avg",
                        labels={"property_type": "Property Type", "area": "Area", "price": "Avg Price ($)"},
                        color_continuous_scale=px.colors.sequential.Viridis
                    ).update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=350
                    )
                ),
                
                # Bedrooms distribution chart
                vm.Graph(
                    id="bedrooms_chart", 
                    title="Bedrooms Distribution by Property Type",
                    figure=px.histogram(
                        df, x="bedrooms", color="property_type",
                        barmode="group",
                        labels={"bedrooms": "Number of Bedrooms", "count": "Number of Properties"},
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    ).update_layout(
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=350
                    )
                ),
                
                # Data table visualization (using scatter plot with hover data)
                vm.Graph(
                    id="property_data", 
                    title="Property Listings Details",
                    figure=px.scatter(
                        df, x="property_type", y="price",
                        color="status",
                        size="square_meters",
                        hover_data=[
                            "agent_name", "location", "area", "neighborhood", 
                            "bedrooms", "bathrooms", "square_meters", 
                            "listing_date", "sale_date", "price_per_sqm"
                        ],
                        labels={"property_type": "Type", "price": "Price ($)"},
                        color_discrete_sequence=px.colors.qualitative.Bold
                    ).update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=400
                    )
                )
            ],
            controls=[
                vm.Filter(column="property_type"),
                vm.Filter(column="status"),
                vm.Filter(column="area"),
                vm.Filter(column="bedrooms"),
                vm.Filter(column="bathrooms")
            ]
        )
    ]
)

# Find an available port and run the dashboard
available_port = find_available_port()
print(f"Launching dashboard on port {available_port}...")
Vizro().build(fallback_dashboard).run(port=available_port)
