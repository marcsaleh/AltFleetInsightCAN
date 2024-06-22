import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Display the logo
#st.image("logo_white_background.jpg", use_column_width=True)

#st.sidebar.image("logo_white_background.jpg", use_column_width=True)

# Sidebar with about section
st.sidebar.title("About AltFleet Insight")

st.sidebar.markdown("""
AltFleet Insight enables users to select their MHDV market of operations and assess the economic implications of deploying alternative fuel technologies using a one-to-one replacement strategy. 
It covers diesel, biodiesel (B20), renewable diesel (R99), and battery electric technologies for all applications, with gasoline, hybrid, and hydrogen fuel cell powertrains available for select markets of operation based on data availability.

This tool is primarily intended to assess different technologies while leveraging financial incentives for small pilot vehicle deployments in Canada. Users should not expect a full fleet transition based on this tool alone.
""")

# Add the Vehicle Class Incentive Table
st.sidebar.title("Federal iMHZEV Incentive Program Amounts")

vehicle_data = {
    "Vehicle Class": [
        "CLASS 7/8 COACH BUS, CLASS 8 FCEVS",
        "CLASS 8 (350 KWH AND UP)",
        "CLASS 8 (UNDER 350 KWH)",
        "CLASS 7",
        "CLASS 6",
        "CLASS 5",
        "CLASS 4",
        "CLASS 3",
        "CLASS 2B"
    ],
    "Maximum Amount": [
        "$200,000",
        "$150,000",
        "$100,000",
        "$100,000",
        "$100,000",
        "$75,000",
        "$75,000",
        "$40,000",
        "$10,000"
    ]
}

vehicle_df = pd.DataFrame(vehicle_data)

# Display the table without the index column
st.sidebar.write(vehicle_df.to_html(index=False), unsafe_allow_html=True)


# Sidebar with disclaimers
st.sidebar.title("Disclaimers")

st.sidebar.markdown("""
- This tool is provided for informational purposes only. The operations and environmental benefits analysis is based on assumptions regarding costs, charging patterns, rates, and other factors. The results of the analysis are approximations and are subject to change. Mobility Futures Lab, Delphi, and the Canadian Transportation Alliance make no warranty, representation, or undertaking, express or implied, as to the accuracy, reliability, or completeness of this analysis.

- All values, including vehicle prices, are based on the best available estimates and can be adjusted as needed.

# Contact:
- For any issues or questions about using this tool, please contact **altfleet@mobilityfutureslab.ca**.
""")


# Main app title (if you haven't added it already)
st.title('AltFleet Insight')

# Automatically load datasets at the start of the app
@st.cache_data
def load_datasets():
    """
    Loads various datasets required for the total cost of ownership (TCO) analysis tool.
    This includes vehicle information, charging infrastructure details, duty cycles, and
    energy prices.
    
    Returns:
        A dictionary of datasets returned as individual dataframes.
    """
    try:
        vehicles_info = pd.read_csv('MHDV_costs_efficiency_final.csv')
        charging_infra_info = pd.read_csv('MHDV_charging_infa_prices_final.csv')
        vehicles_dutycycles = pd.read_csv('MHDV_duty_cycles_final.csv')
        energy_price_province = pd.read_csv('province_energy_prices.csv')

        vehicles_info['Weight_Confi'] = vehicles_info['WeightClass'] + " " + vehicles_info['Configuration']
        vehicles_dutycycles['Weight_Confi'] = vehicles_dutycycles['WeightClass'] + " " + vehicles_dutycycles['Configuration']
        charging_infra_info['charging_models'] = charging_infra_info['PowerLevel'] + " " + charging_infra_info['PortConfiguration']

        return vehicles_info, charging_infra_info, vehicles_dutycycles, energy_price_province
    
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return None

vehicles_info, charging_infra_info, vehicles_dutycycles, energy_price_province = load_datasets()

# Section title for Market of Operations
st.header('1. Market of Operations')

# Function to get the user's province or territory
def get_user_province_territory():
    provinces_and_territories = ["Alberta", "British Columbia", "Manitoba", "New Brunswick", 
                                 "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia", 
                                 "Nunavut", "Ontario", "Prince Edward Island", "Quebec", 
                                 "Saskatchewan", "Yukon"]
    user_province = st.selectbox("Select the province where your fleet is located:",
                                 options=[""] + provinces_and_territories,
                                 format_func=lambda x: "Select a province" if x == "" else x)
    return user_province

user_province = get_user_province_territory()

# Function to get the vehicle application from the user
def get_user_vehicleapplication():
    vehicle_applications = ["Passenger Transport", "Freight and Cargo", "Specialized Services"]
    user_application = st.selectbox("Select vehicle application:",
                                    options=[""] + vehicle_applications,
                                    format_func=lambda x: "Select a vehicle application" if x == "" else x)
    return user_application

user_application = get_user_vehicleapplication()

# Function to get the user's vehicle configuration
def get_user_vehicle_configuration(user_application, vehicles_dutycycles):
    if user_application:
        filtered_df = vehicles_dutycycles[vehicles_dutycycles['VehicleApplication'] == user_application]
        unique_configurations = filtered_df['Configuration'].unique()
        vehicle_configuration = st.selectbox("Select the vehicle configuration:",
                                             options=[""] + list(unique_configurations),
                                             format_func=lambda x: "Select a vehicle configuration" if x == "" else x,
                                             help = "Class 8 tractors are day cabs due to ZEV focus, with long-haul options still developing.")
        return vehicle_configuration
    st.write("Please select a vehicle application first.")
    return None

user_configuration = get_user_vehicle_configuration(user_application, vehicles_dutycycles)

# Function to get the user's vehicle weight class
def get_user_vehicle_weightclass(user_configuration, vehicles_dutycycles):
    if not user_application:
        return None, None
    if user_configuration:
        filtered = vehicles_dutycycles[vehicles_dutycycles['Configuration'] == user_configuration]
        unique_weightClasses = filtered['WeightClass'].unique()
        vehicle_weightClass = st.selectbox("Select the vehicle weight class you operate in:",
                                           options=[""] + list(unique_weightClasses),
                                           format_func=lambda x: "Select a vehicle weight class" if x == "" else x)
        if vehicle_weightClass:
            user_weight_configuration = vehicle_weightClass + " " + user_configuration
            return vehicle_weightClass, user_weight_configuration
        return None, None
    else:
        st.write("Please select a vehicle configuration first.")
    return None, None

vehicle_weightClass, user_weight_configuration = get_user_vehicle_weightclass(user_configuration, vehicles_dutycycles)


# Section title for Technologies Assessed
st.header('2. Technologies Assessed')


def get_existing_fuel(user_weight_configuration, vehicles_info):
    """
    Determines the existing fuel technology based on user input through a Streamlit dropdown menu.

    Parameters:
        user_weight_configuration (str): The user's weight and configuration.
        vehicles_info (DataFrame): A DataFrame containing information about vehicles, including powertrain and configuration.

    Returns:
        str or None: The existing fuel technology selected by the user, or None if no input was provided.
    """
    if not user_weight_configuration:
        st.write("Please select a vehicle configuration and weight class first.")
        return None

    # Filter vehicles that are viable for gasoline
    vehicles_info_gasoline = vehicles_info[vehicles_info["Powertrain"] == "Gasoline"]
    gasoline_weight_configurations = vehicles_info_gasoline["Weight_Confi"].unique()
    
    # Default existing fuel is diesel at a minimum
    existing_fuels = ["Diesel"]
    
    # If the user configuration is in the gasoline configurations, add gasoline to the options
    if user_weight_configuration in gasoline_weight_configurations:
        existing_fuels.append("Gasoline")

    # Streamlit dropdown for selecting existing fuel
    existing_fuel = st.selectbox(
        "Select the fuel type you currently use:",
        options=[""] + existing_fuels,
        format_func=lambda x: "Select a fuel type" if x == "" else x
    )
    
    # Return the selected fuel type if valid, otherwise None
    return existing_fuel if existing_fuel else None

# Example usage within the app
# Assuming 'vehicles_info' DataFrame and 'user_weight_configuration' are defined
existing_fuel = get_existing_fuel(user_weight_configuration, vehicles_info)
#if existing_fuel:
#    st.write(f"Selected Existing Fuel: {existing_fuel}")
#else:
#    st.write("No existing fuel type selected yet.")


def select_alternative_fuel(user_weight_configuration, vehicles_info):
    """
    Allows the user to select an alternative fuel technology based on the vehicle configuration.

    Parameters:
        user_weight_configuration (str): The configuration of the vehicle selected by the user.
        vehicles_info (DataFrame): DataFrame containing vehicle information, including powertrains.

    Returns:
        str or None: The alternative fuel technology selected by the user, or None if no input was provided.
    """
    if not user_weight_configuration:
        #st.write("Please select a vehicle configuration and weight class first.")
        return None

    # Filter vehicles that are viable for hydrogen fuel cell and hybrid technologies
    vehicles_info_hydrogen = vehicles_info[vehicles_info["Powertrain"] == "Hydrogen Fuel Cell"]
    hydrogen_weight_configurations = vehicles_info_hydrogen["Weight_Confi"].unique()
    
    vehicles_info_hybrid = vehicles_info[vehicles_info["Powertrain"] == "HEV"]
    hybrid_weight_configurations = vehicles_info_hybrid["Weight_Confi"].unique()

    # Default alternative fuels
    evaluated_fuels = ["Biodiesel B20", "Renewable Diesel R99", "Battery electric"]

    # Add specific fuels based on configuration checks
    if user_weight_configuration in hydrogen_weight_configurations:
        evaluated_fuels.append("Hydrogen Fuel Cell")
        
    if user_weight_configuration in hybrid_weight_configurations:
        evaluated_fuels.append("HEV")

    # Streamlit dropdown for selecting alternative fuel
    evaluated_fuel = st.selectbox(
        "Select the alternative fuel type you are exploring:",
        options=[""] + evaluated_fuels,
        format_func=lambda x: "Select an alternative fuel type" if x == "" else x
    )
    
    # Return the selected fuel type if valid, otherwise None
    return evaluated_fuel if evaluated_fuel else None

# Example usage within the app
# Assuming 'vehicles_info' DataFrame is defined and 'user_weight_configuration' is obtained from previous selections
evaluated_fuel = select_alternative_fuel(user_weight_configuration, vehicles_info)
#if evaluated_fuel:
#    st.write(f"Selected Alternative Fuel: {evaluated_fuel}")
#else:
#    st.write("No alternative fuel type selected yet.")




def print_fuel_efficiency_and_decide_override(user_weight_configuration, existing_fuel, evaluated_fuel, vehicles_info):
    """
    Streamlit app function to compare fuel efficiencies between existing and evaluated fuel options based on user input or defaults.
    """
    if not user_weight_configuration:
        return None, None
    if not ( existing_fuel and evaluated_fuel):
        st.write("Please select all required fields above.")
        return None, None

    # Get existing fuel efficiency
    existing_fuel_efficiency_default = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == existing_fuel),
        'FuelEfficiencyCAD'
    ].iloc[0]

    # Get evaluated fuel efficiency
    evaluated_fuel_efficiency_default = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == evaluated_fuel),
        'FuelEfficiencyCAD'
    ].iloc[0]

    # Collect user input for existing vehicle fuel efficiency
    existing_fuel_efficiency = st.number_input(
        "Existing vehicle fuel efficiency (L/100 km):",
        value=float(existing_fuel_efficiency_default),
        format="%.2f"
    )
    
    # Determine the prompt for the evaluated fuel efficiency based on the fuel type
    if evaluated_fuel == "Battery electric":
        prompt = "Alternative vehicle fuel efficiency (kWh/km):"
    elif evaluated_fuel == "Hydrogen Fuel Cell":
        prompt = "Alternative vehicle fuel efficiency (kg H2/100 km):"
    else:
        prompt = "Alternative vehicle fuel efficiency (L/100 km):"
    
    # Collect user input for alternative vehicle fuel efficiency
    evaluated_fuel_efficiency = st.number_input(
        prompt,
        value=float(evaluated_fuel_efficiency_default),
        format="%.2f"
    )

    return existing_fuel_efficiency, evaluated_fuel_efficiency

# Example usage within Streamlit
# Assuming 'vehicles_dutycycles' DataFrame and 'user_weight_configuration' are properly defined
existing_fuel_efficiency, evaluated_fuel_efficiency = print_fuel_efficiency_and_decide_override(user_weight_configuration, existing_fuel, evaluated_fuel, vehicles_info)
#st.write(f"Existing Fuel Efficiency: ${existing_fuel_efficiency}")
#st.write(f"Alternative Fuel Efficiecny: ${evaluated_fuel_efficiency}")


def get_n_alternative_fuel_vehicles():
    """
    Allows the user to input the number of alternative fuel vehicles they plan to purchase.
    
    Returns:
        int or None: The number of alternative fuel vehicles the user intends to purchase, or None if no input was provided.
    """
    # Use Streamlit's number_input to get user input
    n_alternative_fuel_vehicles = st.number_input(
        "How many vehicles do you want to purchase?",
        min_value=0,  # Minimum value set to 0 to avoid negative numbers
        value=0,      # Default value set to 0
        step=1,       # Increment by 1
        format="%d"   # Ensure the input is treated as an integer
    )
    
    # The function directly returns the number of vehicles if greater than 0, otherwise None
    return n_alternative_fuel_vehicles if n_alternative_fuel_vehicles > 0 else None

# Example usage in the Streamlit app
n_vehicles = get_n_alternative_fuel_vehicles()
#if n_vehicles is not None:
#    st.write(f"You have chosen to purchase {n_vehicles} alternative fuel vehicles.")
##else:
#    st.write("No vehicles chosen yet.")


# Section title for Operational Conditions
st.header('3. Operational Conditions')

def get_user_daily_distance(user_weight_configuration, vehicles_dutycycles):
    if user_weight_configuration:
        # Extract the default average daily distance based on the vehicle configuration
        default_distance = vehicles_dutycycles.loc[
            vehicles_dutycycles['Weight_Confi'] == user_weight_configuration, 'average_daily_distance'
        ].values[0]
        
        # Display default distance and allow user to override if desired
        daily_distance = st.number_input(
            f"Average daily distance traveled for {user_weight_configuration} (km):",
            min_value=0,
            value=int(default_distance),
            step=5,
            format="%d"
        )
        return daily_distance
    else:
        st.write("Please select a vehicle configuration and weight class first.")
        return None

# Usage of the function is delayed until user_weight_configuration is defined
daily_distance = get_user_daily_distance(user_weight_configuration, vehicles_dutycycles)
# st.write(f"The daily distance used for calculations: {daily_distance} km")

def get_user_yearly_days_operation(user_weight_configuration, vehicles_dutycycles):
    if user_weight_configuration:
        # Fetch the default number of operation days based on the vehicle configuration
        default_days_operations = vehicles_dutycycles.loc[
            vehicles_dutycycles['Weight_Confi'] == user_weight_configuration, 'yearly_days_operation'
        ].values[0]

        # Streamlit number input for user to modify default days of operation
        yearly_days_operations = st.number_input(
            "Days of operation per year (days):",
            min_value=0,
            value=int(default_days_operations),
            step=5,
            format="%d"
        )
        return yearly_days_operations
    else:
        #st.write("Please select a vehicle configuration and weight class first.")
        return None

yearly_days_operations = get_user_yearly_days_operation(user_weight_configuration, vehicles_dutycycles)
# st.write(f"The number of operation days per year: {yearly_days_operations}")

def get_user_vehicle_lifetime(user_weight_configuration, vehicles_dutycycles):
    if user_weight_configuration:
        # Fetch the default vehicle lifetime based on the vehicle configuration
        default_vehicle_lifetime = vehicles_dutycycles.loc[
            vehicles_dutycycles['Weight_Confi'] == user_weight_configuration, 'years_ownership'
        ].values[0]

        # Streamlit number input for user to modify default vehicle lifetime
        vehicle_lifetime = st.number_input(
            "Vehicle lifetime (years):",
            min_value=0,
            value=int(default_vehicle_lifetime),
            step=1,
            format="%d"
        )
        return vehicle_lifetime
    else:
        #st.write("Please select a vehicle configuration and weight class first.")
        return None


vehicle_lifetime = get_user_vehicle_lifetime(user_weight_configuration, vehicles_dutycycles)
# st.write(f"The expected vehicle lifetime: {vehicle_lifetime} years")


# Section title for Financial Assumptions
st.header('4. Financial Assumptions')

def get_user_discount_rate():
    """
    Streamlit app function to get a discount rate from the user.
    The user inputs a discount rate, and the app uses this rate directly or defaults to 0.03 if the input is outside the acceptable range (0 to 1).
    """
    # Use st.number_input to ensure that the input is a float and provide a default and range
    discount_rate = st.number_input("Enter discount rate:", min_value=0.0, max_value=1.0, value=0.03, format="%.2f")
    
    # Display the discount rate directly; no need for a button
    return discount_rate

# This part runs the function in the Streamlit app
discount_rate = get_user_discount_rate()
#st.write(f"Discount Rate: {discount_rate:.2f}")


def print_vehicle_fuelcost_and_decide_override(energy_price_province, user_province, existing_fuel, evaluated_fuel):
    """
    Streamlit app function to compare fuel costs between existing and evaluated fuel types based on user input or defaults.
    """
    if (user_province and existing_fuel and evaluated_fuel):
        # Fetch default fuel prices based on the province and fuel type
        existing_fuel_price_default = energy_price_province.loc[
            (energy_price_province['province'] == user_province),
            existing_fuel
        ].iloc[0]
        
        evaluated_fuel_price_default = energy_price_province.loc[
            (energy_price_province['province'] == user_province),
            evaluated_fuel
        ].iloc[0]
        
        # Define user input fields for existing and alternative fuel costs
        if existing_fuel == "Diesel":
            existing_fuel_price = st.number_input("Diesel fuel cost ($/L):", value=float(existing_fuel_price_default), format="%.2f")
        elif existing_fuel == "Gasoline":
            existing_fuel_price = st.number_input("Gasoline fuel cost ($/L):", value=float(existing_fuel_price_default), format="%.2f")

        # Define user input fields based on the evaluated fuel type
        if evaluated_fuel == "Battery electric":
            evaluated_fuel_price = st.number_input("Charging cost ($/kWh):", value=float(evaluated_fuel_price_default), format="%.2f", help ="Please account for demand charges in your cost per kWh for deployments large enough for these charges to be significant.")
        elif evaluated_fuel == "HEV":
            evaluated_fuel_price = st.number_input("Diesel fuel cost ($/L) for HEV:", value=float(evaluated_fuel_price_default), format="%.2f")
        elif evaluated_fuel == "Biodiesel B20":
            evaluated_fuel_price = st.number_input("Biodiesel B20 fuel cost ($/L):", value=float(evaluated_fuel_price_default), format="%.2f")
        elif evaluated_fuel == "Renewable Diesel R99":
            evaluated_fuel_price = st.number_input("Renewable Diesel R99 fuel cost ($/L):", value=float(evaluated_fuel_price_default), format="%.2f")
        elif evaluated_fuel == "Hydrogen Fuel Cell":
            evaluated_fuel_price = st.number_input("Hydrogen fuel cost ($/kg):", value=float(evaluated_fuel_price_default), format="%.2f")

        return existing_fuel_price, evaluated_fuel_price
    
    else:
        st.write("Please complete previous sections first.")
        return None, None

# Example usage within Streamlit
existing_fuel_price, evaluated_fuel_price = print_vehicle_fuelcost_and_decide_override(
        energy_price_province, user_province, existing_fuel, evaluated_fuel)
#st.write(f"Existing Fuel Cost: ${existing_fuel_price} per unit")
#st.write(f"Evaluated Fuel Cost: ${evaluated_fuel_price} per unit")


st.subheader("4.1 Vehicle")

def fetch_fuel_vehicle_prices(user_weight_configuration, existing_fuel, evaluated_fuel, vehicles_info):
    """
    Fetches and allows user input for the purchase prices of existing and evaluated fuel vehicles based on their configurations.

    Parameters:
        user_weight_configuration (str): Configuration of the vehicle selected by the user.
        existing_fuel (str): Fuel type of the existing vehicle.
        evaluated_fuel (str): Fuel type of the evaluated vehicle.
        vehicles_info (DataFrame): DataFrame containing vehicle information including price.

    Returns:
        tuple: Containing the user input or default prices for existing and evaluated vehicle purchases.
    """
    if (user_weight_configuration and existing_fuel and evaluated_fuel):
        # Fetch existing vehicle purchase price from the dataset
        existing_fuel_vehicle_price_default = vehicles_info.loc[
            (vehicles_info['Weight_Confi'] == user_weight_configuration) & 
            (vehicles_info['Powertrain'] == existing_fuel),
            'Default_price'
        ].iloc[0]

        # Fetch evaluated fuel vehicle purchase price from the dataset
        evaluated_fuel_vehicle_price_default = vehicles_info.loc[
            (vehicles_info['Weight_Confi'] == user_weight_configuration) & 
            (vehicles_info['Powertrain'] == evaluated_fuel),
            'Default_price'
        ].iloc[0]

        # User inputs for existing and evaluated vehicle prices
        existing_fuel_vehicle_price = st.number_input(
            "Existing vehicle purchase price ($):",
            value=int(existing_fuel_vehicle_price_default),
            step=5000,
            format="%d",
            key="existing_fuel_price"
        )

        evaluated_fuel_vehicle_price = st.number_input(
            "Alternative vehicle purchase price ($):",
            value=int(evaluated_fuel_vehicle_price_default),
            step=5000,
            format="%d",
            key="evaluated_fuel_price"
        )
        return existing_fuel_vehicle_price, evaluated_fuel_vehicle_price
    else:
        st.write("Please complete previous sections first.")
        return None, None

# Example usage within the app
# Define these variables based on earlier selections in your app
existing_price, evaluated_price = fetch_fuel_vehicle_prices(user_weight_configuration, existing_fuel, evaluated_fuel, vehicles_info)
#st.write(f"Existing Vehicle Price: ${existing_price}")
#st.write(f"Evaluated Vehicle Price: ${evaluated_price}")


def get_user_vehicle_incentive_amount():
    """
    Allows the user to input the total amount of federal and provincial subsidies available for an alternative vehicle.

    Returns:
        float or None: The total subsidy amount for an alternative vehicle, or None if no input was provided.
    """
    # Streamlit number input to get user input for subsidy amount
    user_vehicle_incentive_amount = st.number_input(
        "Total federal and provincial subsidy per alternative vehicle ($):",
        min_value=0.0,  # Set a minimum value to avoid negative subsidies
        value=0.0,      # Default value set to 0.0
        step=5000.0,     # Step size to increment the subsidy amount
        format="%.2f"   # Format the input to display two decimal places
    )
    
    # Return the subsidy amount; returns 0 if no value is entered
    return user_vehicle_incentive_amount if user_vehicle_incentive_amount > 0 else 0

# Example usage in the Streamlit app
user_vehicle_incentive_amount = get_user_vehicle_incentive_amount()
#if user_vehicle_incentive_amount is not None:
#    st.write(f"Total subsidy amount specified: ${user_vehicle_incentive_amount}")
#else:
#    st.write("No subsidy amount specified.")


def print_vehicle_maintenance_and_decide_override(user_weight_configuration, existing_fuel, evaluated_fuel, vehicles_info):
    """
    Displays maintenance costs for existing and evaluated vehicles based on their configurations and allows the user to override these values.

    Parameters:
        user_weight_configuration (str): Configuration of the vehicle.
        existing_fuel (str): Fuel type of the existing vehicle.
        evaluated_fuel (str): Fuel type of the evaluated vehicle.
        vehicles_info (DataFrame): DataFrame containing vehicle information including maintenance costs.

    Returns:
        tuple: Containing the potentially overridden maintenance costs for existing and evaluated vehicles.
    """
    if (user_weight_configuration and existing_fuel and evaluated_fuel):
        # Fetch default maintenance costs from the dataset
        existing_fuel_maintenance_default = vehicles_info.loc[
            (vehicles_info['Weight_Confi'] == user_weight_configuration) & 
            (vehicles_info['Powertrain'] == existing_fuel), 
            'Maintenance'
        ].iloc[0]

        evaluated_fuel_maintenance_default = vehicles_info.loc[
            (vehicles_info['Weight_Confi'] == user_weight_configuration) & 
            (vehicles_info['Powertrain'] == evaluated_fuel), 
            'Maintenance'
        ].iloc[0]

        # User inputs for existing and evaluated vehicle maintenance costs
        existing_fuel_maintenance = st.number_input(
            "Existing vehicle maintenance ($/km):",
            value=float(existing_fuel_maintenance_default),
            format="%.2f",
            key="existing_maintenance"
        )

        evaluated_fuel_maintenance = st.number_input(
            "Alternative vehicle maintenance ($/km):",
            value=float(evaluated_fuel_maintenance_default),
            format="%.2f",
            key="evaluated_maintenance",
            help= "Maintenance costs for battery electric and hydrogen fuel cell vehicles are estimated based on industry expectations but can vary as these technologies are new and data is limited."
        )
        
        return existing_fuel_maintenance, evaluated_fuel_maintenance
    else:
        return None, None

# Example usage within the app
existing_maintenance, evaluated_maintenance = print_vehicle_maintenance_and_decide_override(
    user_weight_configuration, existing_fuel, evaluated_fuel, vehicles_info
)
#st.write(f"Final Existing Vehicle Maintenance: ${existing_maintenance} per km")
#st.write(f"Final Evaluated Vehicle Maintenance: ${evaluated_maintenance} per km")


def estimate_fuel_costs_per_km(existing_fuel_price, existing_fuel_efficiency, evaluated_fuel_price, evaluated_fuel_efficiency, evaluated_fuel):
    """
    Estimates the fuel cost per kilometer for both existing and evaluated vehicle technologies based on the 
    vehicle's fuel efficiency and the current fuel prices.

    Parameters:
        existing_fuel_price (float): The current price of fuel for the existing vehicle technology ($ per liter or equivalent unit).
        existing_fuel_vehicle_efficiency (float): The fuel efficiency of the existing vehicle (km per liter or equivalent unit).
        evaluated_fuel_price (float): The current price of fuel for the evaluated vehicle technology ($ per liter or equivalent unit).
        evaluated_fuel_vehicle_efficiency (float): The fuel efficiency of the evaluated vehicle (km per liter or equivalent unit).

    Returns:
        tuple: A tuple containing the estimated fuel costs per kilometer for the existing and evaluated vehicles.

    """
    if all(v is not None for v in [existing_fuel_price, existing_fuel_efficiency, evaluated_fuel_price, evaluated_fuel_efficiency, evaluated_fuel]):
        # Calculate fuel cost per kilometer for existing technology
        # diesel or gasoline price ($/km) = ($/L) / (L/100km)
        existing_fuel_perkm = existing_fuel_price * existing_fuel_efficiency /100

        # Calculate fuel cost per kilometer for evaluated technology
        if evaluated_fuel == "Battery electric":
            evaluated_fuel_perkm = evaluated_fuel_price * evaluated_fuel_efficiency
        elif evaluated_fuel == "HEV":
            evaluated_fuel_perkm = evaluated_fuel_price * evaluated_fuel_efficiency /100
        elif evaluated_fuel == "Biodiesel B20":
            evaluated_fuel_perkm = evaluated_fuel_price * evaluated_fuel_efficiency / 100
        elif evaluated_fuel == "Renewable Diesel R99":
            evaluated_fuel_perkm = evaluated_fuel_price * evaluated_fuel_efficiency /100
        elif evaluated_fuel == "Hydrogen Fuel Cell":
            evaluated_fuel_perkm = evaluated_fuel_price * evaluated_fuel_efficiency / 100

        return existing_fuel_perkm, evaluated_fuel_perkm
    else:
        return None, None

existing_fuel_perkm, evaluated_fuel_perkm = estimate_fuel_costs_per_km(existing_fuel_price, existing_fuel_efficiency, evaluated_fuel_price, evaluated_fuel_efficiency, evaluated_fuel)

# get insurance
def get_user_insurance_rates():
    """
    Get insurance rates from user input using Streamlit.
    """
    existing_vehicle_insurance = 0
    alternative_vehicle_insurance = 0

    activate_insurance = st.checkbox("Include Vehicle Insurance")

    if activate_insurance:
        existing_vehicle_insurance = st.number_input("Enter existing vehicle insurance cost ($/km):", min_value=0.0, max_value = 1.0, value = 0.0,  step=0.01)
        alternative_vehicle_insurance = st.number_input("Enter alternative vehicle insurance cost ($/km):", min_value=0.0, max_value = 1.0,value = 0.0,  step=0.01)
    return existing_vehicle_insurance, alternative_vehicle_insurance

existing_vehicle_insurance, alternative_vehicle_insurance = get_user_insurance_rates()

# depriactive
def get_user_depreciation_rates():
    """
    Asks the user for the yearly depreciation rates of the existing and alternative vehicles.
    """
    existing_vehicle_depreciation = None
    alternative_vehicle_depreciation = None

    activate_depreciation = st.checkbox("Include Vehicle Resale at end of lifetime")

    if activate_depreciation:
        existing_vehicle_depreciation = st.number_input(
            "Enter existing vehicle yearly depreciation rate (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=5.0,
        )

        alternative_vehicle_depreciation = st.number_input(
            "Enter alternative vehicle yearly depreciation rate (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=5.0,
        )

    return existing_vehicle_depreciation, alternative_vehicle_depreciation

existing_vehicle_depreciation, alternative_vehicle_depreciation = get_user_depreciation_rates()


def collect_charging_refuelling_infrastrcture_costs(evaluated_fuel, chargingInfra_info):
    if evaluated_fuel:

        alternative_with_refuelling = ['Biodiesel B20','Renewable Diesel R99', 'Hydrogen Fuel Cell', 'HEV']
        
        if evaluated_fuel in alternative_with_refuelling:
            st.subheader("4.2 Refuelling Infrastructure")
            charging_refuelling_infra_cost = st.number_input("Total refuelling infrastructure cost ($):", min_value=0.0, value=0.0, step= 5000.0, format="%.2f")
            user_chargerRefuelling_incentive_amount = st.number_input("Total federal and provincial subsidy for refuelling infrastructure ($):", min_value=0.0, value=0.0, step= 5000.0,  format="%.2f")
            
            return 0, 0, charging_refuelling_infra_cost, user_chargerRefuelling_incentive_amount
        
        elif evaluated_fuel == "Battery electric":
            st.subheader("4.2 Charging Infrastructure")
            options = ['Directly input total charging infrastructure cost', 'Estimate charging infrastructure cost from the bottom up']
            user_charging_infra_approach = st.selectbox("Select charging infrastructure cost estimation approach:", options)
            
            if user_charging_infra_approach == options[0]:
                charging_refuelling_infra_cost = st.number_input("Total charging infrastructure cost including stations, construction and upgrades ($):", min_value=0.0, value=0.0, step= 5000.0, format="%.0f")
                user_chargerRefuelling_incentive_amount = st.number_input("Total federal and provincial subsidy for charging infrastructure ($):", min_value=0.0, value=0.0, step= 5000.0, format="%.0f")
                
                return 0, 0, charging_refuelling_infra_cost, user_chargerRefuelling_incentive_amount
            
            elif user_charging_infra_approach == options[1]:
                st.subheader("Select chargers", help = "Choose chargers based on your needs. Lower power chargers (7.7 kW to 19.2 kW) suit shorter daily distances and extended parking. Higher power chargers (24 kW to 350 kW) are ideal for higher daily mileage and quick turnaround times. Dual ports are mainly used when the charging of vehicles can be staggered.")
                charging_models = chargingInfra_info['charging_models'].tolist()
                charging_models_price = chargingInfra_info['Price'].tolist()
                
                number_chargers_list = []
                charging_station_costs = 0
                
                for i, model in enumerate(charging_models):
                    cols = st.columns(2)
                    with cols[0]:
                        new_price = st.number_input(f"Cost per {model} ($):", min_value=0.0, value=float(charging_models_price[i]), step = 500.0, format="%.2f", key=f"price_{i}")
                    with cols[1]:
                        number_of_chargers = st.number_input(f"Number of {model} chargers:", min_value=0, value=0, key=f"num_{i}")
                    
                    charging_models_price[i] = new_price
                    number_chargers_list.append(number_of_chargers)
                    charging_station_costs += new_price * number_of_chargers
                
                infra_constr_grid_upgrade_costs = st.number_input("Charging infrastructure construction and grid upgrade cost ($):", min_value=0.0, value=0.0,step = 5000.0, format="%.2f")
                charging_refuelling_infra_cost = charging_station_costs + infra_constr_grid_upgrade_costs
                st.write(f"Total Charging Infrastructure cost ($): {charging_refuelling_infra_cost:.2f}")
                
                user_chargerRefuelling_incentive_amount = st.number_input("Total federal and provincial subsidy for charging infrastructure ($):", min_value=0.0, value=0.0, step = 5000.0, format="%.2f")
                
                return charging_station_costs, infra_constr_grid_upgrade_costs, charging_refuelling_infra_cost, user_chargerRefuelling_incentive_amount
    else:
        return None, None, None, None
# Assuming chargingInfra_info is available as a DataFrame or similar structure in your context
# If not, you'll need to define or load it accordingly
charging_station_costs, infra_constr_grid_upgrade_costs, total_infra_cost, user_chargerRefuelling_incentive_amount = collect_charging_refuelling_infrastrcture_costs(evaluated_fuel, charging_infra_info)
#st.write(f"Charging station costs: ${charging_station_costs} per unit")
#st.write(f"Construction and grid upgrade costs: ${infra_constr_grid_upgrade_costs} per unit")
#st.write(f"Total Charging-Refueling Infrastructure costs: ${charging_refuelling_infra_cost} per unit")
#st.write(f"Total Charging-Refuelling Infrastructure subsidy: ${user_chargerRefuelling_incentive_amount} per unit")


st.header("5. Results")
st.subheader("5.1 Project costs")


def discounted_TCO(base_tech, alternative_tech, n_vehicles, basevehicle_cost, altvehicle_cost, refueling_station_cost,
                   refueling_station_infra, maintenance_base, maintenance_alt, fuel_base, fuel_alt, v_lifetime,
                   daily_distance, days_operation, vehicle_subsidy, infrastructure_subsidy, discount_rate, user_province, energy_price_province, total_infra_cost,
                   existing_vehicle_insurance, alternative_vehicle_insurance, existing_vehicle_depreciation, alternative_vehicle_depreciation):
    
    # Convert all numerical inputs to appropriate types
    n_vehicles = float(n_vehicles)
    basevehicle_cost = float(basevehicle_cost)
    altvehicle_cost = float(altvehicle_cost)
    refueling_station_cost = float(refueling_station_cost)
    refueling_station_infra = float(refueling_station_infra)
    maintenance_base = float(maintenance_base)
    maintenance_alt = float(maintenance_alt)
    fuel_base = float(fuel_base)
    fuel_alt = float(fuel_alt)
    v_lifetime = int(v_lifetime)
    daily_distance = float(daily_distance)
    days_operation = float(days_operation)
    vehicle_subsidy = float(vehicle_subsidy)
    infrastructure_subsidy = float(infrastructure_subsidy)
    discount_rate = float(discount_rate)
    existing_vehicle_insurance = float(existing_vehicle_insurance)
    alternative_vehicle_insurance = float(alternative_vehicle_insurance)
    
    # Tax rate per province
    prinvincial_tax = energy_price_province.loc[(energy_price_province['province'] == user_province)]['taxes_perc'].iloc[0]/100
    
    # Initialize empty dataframe where yearly cost will be added
    df_total_cost = pd.DataFrame(columns=['Year', 'DCO_base', 'DCO_alternative', 'DCO_alternative_Withincentive'])
    
    # If subsidies are not present, do not calculate DCO_alternative_Withincentive
    plot_incentive = vehicle_subsidy > 0 or infrastructure_subsidy > 0

    # Iterate with loop to add values for each year
    for year in range(v_lifetime + 1):
        discount_factor = 1 / ((1 + discount_rate) ** year)
        
        # For year zero, add capital costs with discount
        if year == 0:
            df_total_cost.loc[year, 'Year'] = year
            df_total_cost.loc[year, 'DCO_base'] = basevehicle_cost * n_vehicles * (1 + prinvincial_tax) * discount_factor
            alt_capital_cost = altvehicle_cost * n_vehicles + (refueling_station_cost + refueling_station_infra if refueling_station_cost > 0 else total_infra_cost)
            df_total_cost.loc[year, 'DCO_alternative'] = alt_capital_cost * discount_factor * (1 + prinvincial_tax)
            if plot_incentive:
                df_total_cost.loc[year, 'DCO_alternative_Withincentive'] = (alt_capital_cost - vehicle_subsidy * n_vehicles - infrastructure_subsidy) * discount_factor * (1 + prinvincial_tax)
        else:
            # Add year
            df_total_cost.loc[year, 'Year'] = year
            # Calculate discounted operational costs for the year
            discounted_op_cost_base = (maintenance_base + fuel_base + existing_vehicle_insurance) * daily_distance * days_operation * n_vehicles * discount_factor
            discounted_op_cost_alt = (maintenance_alt + fuel_alt + alternative_vehicle_insurance) * daily_distance * days_operation * n_vehicles * discount_factor
            
            # Add discounted costs to cumulative costs from previous years
            df_total_cost.loc[year, 'DCO_base'] = df_total_cost.loc[year - 1, 'DCO_base'] + discounted_op_cost_base
            df_total_cost.loc[year, 'DCO_alternative'] = df_total_cost.loc[year - 1, 'DCO_alternative'] + discounted_op_cost_alt
            if plot_incentive:
                df_total_cost.loc[year, 'DCO_alternative_Withincentive'] = df_total_cost.loc[year - 1, 'DCO_alternative_Withincentive'] + discounted_op_cost_alt

    # Calculate resale value only if depreciation inputs are provided
    if existing_vehicle_depreciation is not None and alternative_vehicle_depreciation is not None and existing_vehicle_depreciation != 0 and alternative_vehicle_depreciation != 0:
        existing_vehicle_depreciation = float(existing_vehicle_depreciation) / 100
        alternative_vehicle_depreciation = float(alternative_vehicle_depreciation) / 100
        
        # Calculate the resale value at the end of the ownership period based on depreciation rates
        resale_value_base = basevehicle_cost * (1 - existing_vehicle_depreciation) ** v_lifetime
        resale_value_alt = altvehicle_cost * (1 - alternative_vehicle_depreciation) ** v_lifetime

        # Calculate the present value of the resale value at the end of the ownership period
        resale_value_base_discounted = resale_value_base / ((1 + discount_rate) ** v_lifetime)
        resale_value_alt_discounted = resale_value_alt / ((1 + discount_rate) ** v_lifetime)
        
        # Subtract the discounted resale value from the total cost at the end of the ownership period
        df_total_cost.loc[v_lifetime, 'DCO_base'] -= resale_value_base_discounted * n_vehicles
        df_total_cost.loc[v_lifetime, 'DCO_alternative'] -= resale_value_alt_discounted * n_vehicles
        if plot_incentive:
            df_total_cost.loc[v_lifetime, 'DCO_alternative_Withincentive'] -= resale_value_alt_discounted * n_vehicles

    # Convert all columns to float for consistency and round to 2 decimal places
    df_total_cost = df_total_cost.astype(float).round(2)
    
    # Check maximum value in 'DCO_alternative' to decide the scale
    max_value = df_total_cost['DCO_alternative'].max()
    if max_value < 1e6:
        scale = 1e3
        ylabel = 'Cumulative Cost of Ownership (Thousands $)'
    else:
        scale = 1e6
        ylabel = 'Cumulative Cost of Ownership (Millions $)'
    
    # Scale the costs for plotting
    df_total_cost[['DCO_base', 'DCO_alternative', 'DCO_alternative_Withincentive']] /= scale

    # Prepare the data for Plotly
    df_long = df_total_cost.melt(id_vars='Year', var_name='Category', value_name='Cost')
    df_long['Category'] = df_long['Category'].replace({
        'DCO_base': base_tech,
        'DCO_alternative': alternative_tech,
        'DCO_alternative_Withincentive': f"{alternative_tech} with subsidies"
    })

    # Create the Plotly figure
    fig = go.Figure()

    # Add the base technology line
    fig.add_trace(go.Scatter(x=df_long[df_long['Category'] == base_tech]['Year'], 
                             y=df_long[df_long['Category'] == base_tech]['Cost'].round(2),
                             mode='lines+markers',
                             name=base_tech,
                             line=dict(color='red')))

    # Add the alternative technology line
    fig.add_trace(go.Scatter(x=df_long[df_long['Category'] == alternative_tech]['Year'], 
                             y=df_long[df_long['Category'] == alternative_tech]['Cost'].round(2),
                             mode='lines+markers',
                             name=alternative_tech,
                             line=dict(color='#1B5E20')))

    # Add the alternative technology with subsidies line
    if plot_incentive:
        fig.add_trace(go.Scatter(x=df_long[df_long['Category'] == f"{alternative_tech} with subsidies"]['Year'], 
                             y=df_long[df_long['Category'] == f"{alternative_tech} with subsidies"]['Cost'].round(2),
                             mode='lines+markers',
                             name=f"{alternative_tech} with subsidies",
                             line=dict(color='#1B5E20', dash='dash')))

    # Update layout
    fig.update_layout(#title="Discounted Total Cost of Ownership Over Time",
                      xaxis_title='Years',
                      yaxis_title=ylabel,
                      legend_title='Technology')

    return fig, df_total_cost


def stacked_bar_DCO(base_tech, alternative_tech, n_vehicles, basevehicle_cost, altvehicle_cost, refueling_station_cost,
                    refueling_station_infra, maintenance_base, maintenance_alt, fuel_base, fuel_alt, v_lifetime,
                    daily_distance, days_operation, vehicle_subsidy, infrastructure_subsidy, discount_rate, user_province, energy_price_province, total_infra_cost,
                    existing_vehicle_insurance, alternative_vehicle_insurance, existing_vehicle_depreciation, alternative_vehicle_depreciation):

    # Convert all inputs to appropriate types
    n_vehicles = float(n_vehicles)
    basevehicle_cost *= n_vehicles
    altvehicle_cost *= n_vehicles
    total_infra_cost = float(total_infra_cost)
    maintenance_base = float(maintenance_base)
    maintenance_alt = float(maintenance_alt)
    fuel_base = float(fuel_base)
    fuel_alt = float(fuel_alt)
    v_lifetime = int(v_lifetime)
    daily_distance = float(daily_distance)
    days_operation = float(days_operation)
    vehicle_subsidy *= n_vehicles
    infrastructure_subsidy = float(infrastructure_subsidy)
    discount_rate = float(discount_rate)
    provincial_tax = energy_price_province.loc[(energy_price_province['province'] == user_province)]['taxes_perc'].iloc[0] / 100
    
    # Determine infrastructure label based on alternative technology
    if alternative_tech == "Battery electric":
        infra_label = "Charging Infrastructure"
    elif alternative_tech in ["Biodiesel B20", "Hydrogen Fuel Cell"]:
        infra_label = "Refuelling Infrastructure"
    else:
        infra_label = "Charging/Refuelling Infrastructure"

    # If subsidies are present, calculate and plot with subsidies
    plot_incentive = vehicle_subsidy > 0 or infrastructure_subsidy > 0

    # Initialize a dictionary to store total discounted costs
    total_costs = {
        base_tech: {'Vehicle': basevehicle_cost * (1 + provincial_tax), 'Maintenance': 0, 'Fuel': 0, 'Insurance': 0}
    }
    
    # Include the infrastructure costs if total_infra_cost is greater than zero
    if total_infra_cost > 0:
        total_costs[alternative_tech] = {'Vehicle': altvehicle_cost * (1 + provincial_tax), infra_label: total_infra_cost * (1 + provincial_tax), 'Maintenance': 0, 'Fuel': 0, 'Insurance': 0}
        if plot_incentive:
            total_costs[alternative_tech + ' (with subsidies)'] = {'Vehicle': (altvehicle_cost - vehicle_subsidy) * (1 + provincial_tax), infra_label: (total_infra_cost - infrastructure_subsidy) * (1 + provincial_tax), 'Maintenance': 0, 'Fuel': 0, 'Insurance': 0}
    else:
        total_costs[alternative_tech] = {'Vehicle': altvehicle_cost * (1 + provincial_tax), 'Maintenance': 0, 'Fuel': 0, 'Insurance': 0}
        if plot_incentive:
            total_costs[alternative_tech + ' (with subsidies)'] = {'Vehicle': (altvehicle_cost - vehicle_subsidy) * (1 + provincial_tax), 'Maintenance': 0, 'Fuel': 0, 'Insurance': 0}

    # Calculate total discounted costs for each category over the vehicle lifetime
    for year in range(1, v_lifetime + 1):
        discount_factor = 1 / ((1 + discount_rate) ** year)
        total_costs[base_tech]['Maintenance'] += maintenance_base * daily_distance * days_operation * n_vehicles * discount_factor
        total_costs[base_tech]['Fuel'] += fuel_base * daily_distance * days_operation * n_vehicles * discount_factor
        if existing_vehicle_insurance not in [None, 0]:
            total_costs[base_tech]['Insurance'] += existing_vehicle_insurance * daily_distance * days_operation * n_vehicles * discount_factor
        for tech in total_costs.keys():
            if tech != base_tech:
                total_costs[tech]['Maintenance'] += maintenance_alt * daily_distance * days_operation * n_vehicles * discount_factor
                total_costs[tech]['Fuel'] += fuel_alt * daily_distance * days_operation * n_vehicles * discount_factor
                if alternative_vehicle_insurance not in [None, 0]:
                    total_costs[tech]['Insurance'] += alternative_vehicle_insurance * daily_distance * days_operation * n_vehicles * discount_factor

    # Calculate resale value only if depreciation inputs are provided
    if existing_vehicle_depreciation is not None and alternative_vehicle_depreciation is not None and existing_vehicle_depreciation != 0 and alternative_vehicle_depreciation != 0:
        existing_vehicle_depreciation = float(existing_vehicle_depreciation)/100
        alternative_vehicle_depreciation = float(alternative_vehicle_depreciation)/100
        
        resale_value_base = basevehicle_cost * (1 - existing_vehicle_depreciation) ** v_lifetime
        resale_value_alt = altvehicle_cost * (1 - alternative_vehicle_depreciation) ** v_lifetime

        # Subtract the present value of the resale value from the vehicle cost
        total_costs[base_tech]['Vehicle'] -= resale_value_base / ((1 + discount_rate) ** v_lifetime)
        for tech in total_costs.keys():
            if tech != base_tech:
                total_costs[tech]['Vehicle'] -= resale_value_alt / ((1 + discount_rate) ** v_lifetime)
    
    # Convert total costs to DataFrame for plotting
    df_total_costs = pd.DataFrame(total_costs).transpose()

    # Define column order dynamically based on presence of infrastructure costs
    columns = ['Vehicle', 'Maintenance', 'Fuel']
    if total_infra_cost > 0:
        columns.insert(1, infra_label)
    if (existing_vehicle_insurance not in [None, 0]) and (alternative_vehicle_insurance not in [None, 0]):
        columns.append('Insurance')
    df_total_costs = df_total_costs[columns]  # Correct order of categories

    # Scaling for display
    max_vehicle_cost = df_total_costs['Vehicle'].max()
    ylabel = 'Total Cost of Ownership (Thousands $)' if max_vehicle_cost < 1e6 else 'Total Cost of Ownership (Millions $)'
    df_total_costs /= 1e3 if max_vehicle_cost < 1e6 else 1e6

    # Plotting the stacked bar chart
    fig = go.Figure()

    # Add each category as a separate trace
    colors = ['#215E21', '#507250', '#7E9E7E', '#AFCFAF', '#D3E6D3']
    for i, column in enumerate(columns):
        fig.add_trace(go.Bar(
            x=df_total_costs.index,
            y=df_total_costs[column].round(2),
            name=column,
            marker_color=colors[i],
            hoverinfo='x+y'
        ))

    # Update layout
    fig.update_layout(
        barmode='stack',
        #title="Total Discounted Cost of Ownership",
        #xaxis_title='Technology',
        yaxis_title=ylabel,
        legend_title='Category',
        legend=dict(x=1, y=0.5)
    )

    return fig


if (existing_fuel and evaluated_fuel and n_vehicles and existing_price and evaluated_price and existing_maintenance and evaluated_maintenance and existing_fuel_perkm and evaluated_fuel_perkm and vehicle_lifetime and daily_distance and yearly_days_operations and discount_rate and user_province):
        
    tab1, tab2 = st.tabs(["Stacked Net Present Value Costs", "Cumulative Costs Over Time"])

    with tab1:
        fig1 = stacked_bar_DCO(existing_fuel, evaluated_fuel, n_vehicles, existing_price, evaluated_price, charging_station_costs,
              infra_constr_grid_upgrade_costs, existing_maintenance, evaluated_maintenance, existing_fuel_perkm, evaluated_fuel_perkm, vehicle_lifetime,
              daily_distance, yearly_days_operations, user_vehicle_incentive_amount, user_chargerRefuelling_incentive_amount, discount_rate, user_province, energy_price_province, total_infra_cost,
              existing_vehicle_insurance, alternative_vehicle_insurance, existing_vehicle_depreciation, alternative_vehicle_depreciation)
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        fig2, df_total_cost = discounted_TCO(existing_fuel, evaluated_fuel, n_vehicles, existing_price, evaluated_price, charging_station_costs,
              infra_constr_grid_upgrade_costs, existing_maintenance, evaluated_maintenance, existing_fuel_perkm, evaluated_fuel_perkm, vehicle_lifetime,
              daily_distance, yearly_days_operations, user_vehicle_incentive_amount, user_chargerRefuelling_incentive_amount, discount_rate, user_province, energy_price_province, total_infra_cost,
               existing_vehicle_insurance, alternative_vehicle_insurance, existing_vehicle_depreciation, alternative_vehicle_depreciation)
        st.plotly_chart(fig2, use_container_width=True)

else:
    st.write("Please complete all input fields.")


# Section title for Emissions reduction
st.subheader('5.2 Project operational emission reductions')


# estimate GHG
def estimateGHG_emissions(user_province, existing_fuel, evaluated_fuel, n_alternative_fuel_vehicles, vehicle_lifetime, daily_distance, yearly_days_operations, energy_price_province, evaluated_fuel_efficiency, vehicles_info):
    if existing_fuel == "Diesel":
        # extract ghg EF
        Diesel_GHG_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == existing_fuel),
        'GHG EF'].iloc[0]
        # estimate GHG emissions
        existing_total_GHG_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * Diesel_GHG_EF
        
    elif existing_fuel == "Gasoline":
        # extract ghg EF
        Gasoline_GHG_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == existing_fuel),
        'GHG EF'].iloc[0]
        # estimate GHG emissions
        existing_total_GHG_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * Gasoline_GHG_EF
        
        
    # estimate GHG emissions
    if evaluated_fuel == "Battery electric":
        # extract grid intensity for user province in gCO2/kWh
        electricity_intensity = energy_price_province.loc[energy_price_province['province'] == user_province, 'grid_intensity'].values[0]
        # estaimte ghg emissions
        alternative_total_GHG_emissions= n_alternative_fuel_vehicles * vehicle_lifetime * evaluated_fuel_efficiency * daily_distance * yearly_days_operations * electricity_intensity
    elif evaluated_fuel == "HEV":
        # extract ghg EF
        HEV_GHG_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == evaluated_fuel),
        'GHG EF'].iloc[0]
        # estimate GHG emissions
        alternative_total_GHG_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * HEV_GHG_EF
    elif evaluated_fuel == "Biodiesel B20":
        B20_GHG_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == evaluated_fuel),
        'GHG EF'].iloc[0]
         # estimate GHG emissions
        alternative_total_GHG_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * B20_GHG_EF
    elif evaluated_fuel == "Renewable Diesel R99":
        R99_GHG_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == evaluated_fuel),
        'GHG EF'].iloc[0]
         # estimate GHG emissions
        alternative_total_GHG_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * R99_GHG_EF
    elif evaluated_fuel == "Hydrogen Fuel Cell":
        # extract hydrogen production intensity for user province in gCO2/kgHydrogen
        hydrogen_intensity = energy_price_province.loc[energy_price_province['province'] == user_province, 'hydrogen_intensity'].values[0]
        # estimate ghg emissions
        alternative_total_GHG_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * evaluated_fuel_efficiency/100 * daily_distance * yearly_days_operations * hydrogen_intensity
        
    return existing_total_GHG_emissions/1000000, alternative_total_GHG_emissions/1000000

if (user_province and existing_fuel and evaluated_fuel and n_vehicles and vehicle_lifetime and daily_distance and yearly_days_operations and evaluated_fuel_efficiency):
    existing_total_GHG_emissions, alternative_total_GHG_emissions = estimateGHG_emissions(user_province, existing_fuel, evaluated_fuel, n_vehicles, vehicle_lifetime, daily_distance, yearly_days_operations, energy_price_province, evaluated_fuel_efficiency, vehicles_info)
else:
    existing_total_GHG_emissions, alternative_total_GHG_emissions = None, None
    "Please complete previous sections first."


# NOx and PM2.5 emission
def estimateNOXPM_emissions(existing_fuel, evaluated_fuel, n_alternative_fuel_vehicles, vehicle_lifetime, daily_distance, yearly_days_operations, energy_price_province, vehicles_info):

    # existing fuel NOx and PM2.5 emissions
    # extract NOX and PM2.5 EFs
    existing_NOx_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == existing_fuel),
        'NOx EF'].iloc[0]
    
    existing_PM25_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == existing_fuel),
        'PM2.5 EF'].iloc[0]
    
    # estimate NOX and PM2.5 emissions
    existing_total_NOX_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * existing_NOx_EF
    existing_total_PM25_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * existing_PM25_EF

    # Alternative fuel NOx and PM2.5 emissions
    # extract NOX and PM2.5 EFs
    alternative_NOx_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == evaluated_fuel),
        'NOx EF'].iloc[0]
    
    alternative_PM25_EF = vehicles_info.loc[
        (vehicles_info['Weight_Confi'] == user_weight_configuration) & (vehicles_info['Powertrain'] == evaluated_fuel),
        'PM2.5 EF'].iloc[0]
    
    # estimate NOX and PM2.5 emissions
    alternative_total_NOX_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * alternative_NOx_EF
    alternative_total_PM25_emissions = n_alternative_fuel_vehicles * vehicle_lifetime * daily_distance * yearly_days_operations * alternative_PM25_EF
    
    
    return existing_total_NOX_emissions, existing_total_PM25_emissions , alternative_total_NOX_emissions, alternative_total_PM25_emissions

if (existing_fuel and evaluated_fuel and n_vehicles and vehicle_lifetime and daily_distance and yearly_days_operations):
    existing_total_NOX_emissions, existing_total_PM25_emissions , alternative_total_NOX_emissions, alternative_total_PM25_emissions = estimateNOXPM_emissions(existing_fuel, evaluated_fuel, n_vehicles, vehicle_lifetime, daily_distance, yearly_days_operations, energy_price_province, vehicles_info)
else:
    existing_total_NOX_emissions, existing_total_PM25_emissions , alternative_total_NOX_emissions, alternative_total_PM25_emissions = None, None, None, None



def print_emission_reductions_streamlit(existing_total_NOX_emissions, existing_total_PM25_emissions, alternative_total_NOX_emissions,
                                        alternative_total_PM25_emissions, existing_total_GHG_emissions, alternative_total_GHG_emissions):
    """
    This function calculates and displays the reductions in GHG, NOx, and PM2.5 emissions in a Streamlit app.

    Parameters:
    - existing_total_NOX_emissions (float): Existing NOx emissions in g.
    - existing_total_PM25_emissions (float): Existing PM2.5 emissions in g.
    - alternative_total_NOX_emissions (float): Alternative NOx emissions in g.
    - alternative_total_PM25_emissions (float): Alternative PM2.5 emissions in g.
    - existing_total_GHG_emissions (float): Existing GHG emissions in tonnes.
    - alternative_total_GHG_emissions (float): Alternative GHG emissions in tonnes.
    """

    # Calculate reductions
    reduction_GHG = existing_total_GHG_emissions - alternative_total_GHG_emissions
    reduction_NOX = (existing_total_NOX_emissions - alternative_total_NOX_emissions)/1000
    reduction_PM25 = (existing_total_PM25_emissions - alternative_total_PM25_emissions)/1000

    # Calculate percentage changes
    percent_change_GHG = (reduction_GHG / existing_total_GHG_emissions) * 100
    percent_change_NOX = (reduction_NOX / existing_total_NOX_emissions) * 100
    percent_change_PM25 = (reduction_PM25 / existing_total_PM25_emissions) * 100

    # Display reductions and percentage changes in Streamlit using larger font size
    col1, col2, col3 = st.columns(3)
    col1.metric("GHG Reduction (CO2eq)", f"{reduction_GHG:.0f} tonnes", f"{-percent_change_GHG:.2f}%", delta_color="inverse")
    col2.metric("NOx Reduction", f"{reduction_NOX:.0f} kg")
    col3.metric("PM2.5 Reduction", f"{reduction_PM25:.0f} kg")

if (existing_total_NOX_emissions is not None and existing_total_PM25_emissions is not None and
    alternative_total_NOX_emissions is not None and alternative_total_PM25_emissions is not None and
    existing_total_GHG_emissions is not None and alternative_total_GHG_emissions is not None):
    print_emission_reductions_streamlit(
        existing_total_NOX_emissions, existing_total_PM25_emissions,
        alternative_total_NOX_emissions, alternative_total_PM25_emissions,
        existing_total_GHG_emissions, alternative_total_GHG_emissions)
