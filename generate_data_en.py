"""Data generation for the oil production company. 2020–2025."""
import random
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT = Path(__file__).parent / 'data.sql'
random.seed(45)


def rd(sy=2020, ey=2025):
    s, e = datetime(sy, 1, 1), datetime(ey, 12, 31)
    return (s + timedelta(days=random.randint(0, (e - s).days))).strftime('%Y-%m-%d')


with open(OUTPUT, 'w', encoding='utf-8') as f:
    # Regions & Fields
    for i in range(1, 11):
        f.write(
            f"INSERT INTO regions (region_id, region_name, country, basin_name) VALUES ({i}, 'Region_{i}', 'Russia', 'Basin_{i}');\n"
        )
    for i in range(1, 26):
        f.write(
            f"INSERT INTO fields (field_id, field_code, field_name, region_id, status, estimated_reserves_mboe) VALUES ({i}, 'FLD-{i:02d}', 'Field_{i}', {random.randint(1, 10)}, 'production', {random.randint(100, 5000)});\n"
        )

    # Well types & Wells
    for i in range(1, 6):
        f.write(
            f"INSERT INTO well_types (well_type_id, type_name, typical_depth_m) VALUES ({i}, 'Type_{i}', {random.randint(1500, 5000)});\n"
        )
    for i in range(1, 201):
        f.write(
            f"INSERT INTO wells (well_id, well_name, field_id, well_type_id, status, depth_m) VALUES ({i}, 'WELL-{i:04d}', {random.randint(1, 25)}, {random.randint(1, 5)}, '{random.choice(['producing', 'shut_in', 'injection'])}', {random.randint(2000, 4500)});\n"
        )

    # Platforms
    for i in range(1, 16):
        f.write(
            f"INSERT INTO platforms (platform_id, platform_name, platform_type, field_id, status, capacity_bopd) VALUES ({i}, 'Platform_{i}', '{random.choice(['onshore', 'offshore_fixed', 'FPSO'])}', {random.randint(1, 25)}, 'operational', {random.randint(10000, 100000)});\n"
        )

    # Production records (daily over 5 years – sample 15000)
    for _ in range(15000):
        wid = random.randint(1, 200)
        f.write(
            f"INSERT INTO production_records (well_id, record_date, oil_bbl, gas_mcf, water_bbl, downtime_hours) VALUES ({wid}, '{rd(2020, 2025)}', {round(random.uniform(100, 5000), 2)}, {round(random.uniform(0, 10000), 2)}, {round(random.uniform(0, 2000), 2)}, {round(random.uniform(0, 12), 2)});\n"
        )

    # Field production (10000)
    for _ in range(10000):
        fid = random.randint(1, 25)
        f.write(
            f"INSERT INTO field_production (field_id, record_date, oil_bbl, gas_mcf, water_bbl) VALUES ({fid}, '{rd(2020, 2025)}', {round(random.uniform(5000, 50000), 2)}, {round(random.uniform(10000, 200000), 2)}, {round(random.uniform(1000, 20000), 2)});\n"
        )

    # Drilling (50 campaigns, 500 operations)
    for i in range(1, 51):
        f.write(
            f"INSERT INTO drilling_campaigns (campaign_id, campaign_name, field_id, start_date, end_date, status, budget_usd) VALUES ({i}, 'Кампания_{i}', {random.randint(1, 25)}, '{rd(2020, 2023)}', '{rd(2021, 2025)}', '{random.choice(['in_progress', 'completed'])}', {random.randint(10000000, 100000000)});\n"
        )
    for i in range(1, 501):
        f.write(
            f"INSERT INTO drilling_operations (well_id, campaign_id, operation_date, depth_reached_m, operation_type, duration_hours, cost_usd) VALUES ({random.randint(1, 200)}, {random.randint(1, 50)}, '{rd(2020, 2025)}', {random.randint(1000, 4000)}, '{random.choice(['drilling', 'casing', 'completion'])}', {round(random.uniform(12, 168), 2)}, {random.randint(500000, 5000000)});\n"
        )

    # Pipelines, Tanks
    for i in range(1, 21):
        f.write(
            f"INSERT INTO pipelines (pipeline_id, pipeline_name, pipeline_type, origin_field_id, length_km, capacity_bopd, status) VALUES ({i}, 'Pipeline_{i}', 'oil', {random.randint(1, 25)}, {random.randint(50, 500)}, {random.randint(50000, 200000)}, 'operational');\n"
        )
    for i in range(1, 51):
        f.write(
            f"INSERT INTO storage_tanks (tank_id, tank_name, field_id, capacity_bbl, current_level_bbl, product_type, status) VALUES ({i}, 'Tank_{i}', {random.randint(1, 25)}, {random.randint(100000, 500000)}, {random.randint(10000, 400000)}, 'crude', 'active');\n"
        )

    # Buyers & Contracts & Liftings
    for i in range(1, 31):
        f.write(
            f"INSERT INTO buyers (buyer_id, buyer_name, country, contract_type) VALUES ({i}, 'Buyer_{i}', '{random.choice(['Russia', 'China', 'Europe', 'India'])}', 'SPOT');\n"
        )
    for i in range(1, 101):
        f.write(
            f"INSERT INTO sales_contracts (contract_id, contract_number, buyer_id, product_type, volume_bbl, price_per_bbl, status) VALUES ({i}, 'OIL-CNT-{i:04d}', {random.randint(1, 30)}, 'crude', {random.randint(100000, 2000000)}, {random.randint(40, 120)}, 'active');\n"
        )
    for i in range(1, 2001):
        f.write(
            f"INSERT INTO liftings (contract_id, lifting_date, volume_bbl, price_per_bbl) VALUES ({random.randint(1, 100)}, '{rd(2020, 2025)}', {round(random.uniform(10000, 200000), 2)}, {random.randint(50, 100)});\n"
        )

    # Operating costs (6000)
    for i in range(1, 6001):
        f.write(
            f"INSERT INTO operating_costs (cost_id, field_id, cost_date, cost_category, amount_usd, well_id) VALUES ({i}, {random.randint(1, 25)}, '{rd(2020, 2025)}', '{random.choice(['labor', 'maintenance', 'chemicals', 'utilities'])}', {random.randint(10000, 500000)}, {random.randint(1, 200)});\n"
        )

    # Employees (200)
    for i in range(1, 201):
        f.write(
            f"INSERT INTO employees (employee_id, first_name, last_name, position, field_id, hire_date, salary_usd) VALUES ({i}, 'Employee_{i}', 'LastName', 'Engineer', {random.randint(1, 25)}, '{rd(2015, 2023)}', {random.randint(80000, 250000)});\n"
        )

    # Safety (300)
    for i in range(1, 301):
        f.write(
            f"INSERT INTO safety_incidents (incident_id, field_id, incident_date, incident_type, severity, lost_time_days) VALUES ({i}, {random.randint(1, 25)}, '{rd(2020, 2025)}', '{random.choice(['LTI', 'TRC', 'spill', 'near_miss'])}', '{random.choice(['low', 'medium', 'high'])}', {random.randint(0, 15)});\n"
        )

    # Reservoir data (2000)
    for i in range(1, 2001):
        f.write(
            f"INSERT INTO reservoir_data (field_id, well_id, data_date, pressure_psi, temperature_c, water_cut_percent, GOR_scf_bbl) VALUES ({random.randint(1, 25)}, {random.randint(1, 200)}, '{rd(2020, 2025)}', {random.randint(2000, 5000)}, {round(random.uniform(60, 120), 2)}, {round(random.uniform(5, 80), 2)}, {round(random.uniform(100, 2000), 2)});\n"
        )


print("Oil company data generated.")

