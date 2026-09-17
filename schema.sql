-- ============================================
-- БАЗА ДАННЫХ: НЕФТЕДОБЫВАЮЩАЯ КОМПАНИЯ
-- ============================================

-- Справочники
CREATE TABLE regions (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    basin_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fields (
    field_id SERIAL PRIMARY KEY,
    field_code VARCHAR(20) UNIQUE NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    region_id INT NOT NULL REFERENCES regions(region_id),
    discovery_date DATE,
    estimated_reserves_mboe DECIMAL(14,2),
    status VARCHAR(30) CHECK (status IN ('exploration', 'development', 'production', 'declining', 'abandoned')),
    water_depth_m INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE well_types (
    well_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    description TEXT,
    typical_depth_m INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wells (
    well_id SERIAL PRIMARY KEY,
    well_name VARCHAR(50) UNIQUE NOT NULL,
    field_id INT NOT NULL REFERENCES fields(field_id),
    well_type_id INT REFERENCES well_types(well_type_id),
    spud_date DATE,
    completion_date DATE,
    status VARCHAR(30) CHECK (status IN ('drilling', 'producing', 'injection', 'shut_in', 'abandoned', 'suspended')),
    depth_m INT,
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE platforms (
    platform_id SERIAL PRIMARY KEY,
    platform_name VARCHAR(100) NOT NULL,
    platform_type VARCHAR(30) CHECK (platform_type IN ('onshore', 'offshore_fixed', 'FPSO', 'jackup', 'semisub')),
    field_id INT REFERENCES fields(field_id),
    installation_date DATE,
    capacity_bopd DECIMAL(12,2),
    status VARCHAR(20) CHECK (status IN ('operational', 'maintenance', 'decommissioned')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE platform_wells (
    pw_id SERIAL PRIMARY KEY,
    platform_id INT NOT NULL REFERENCES platforms(platform_id),
    well_id INT NOT NULL REFERENCES wells(well_id),
    connection_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Добыча
CREATE TABLE production_records (
    production_id SERIAL PRIMARY KEY,
    well_id INT NOT NULL REFERENCES wells(well_id),
    record_date DATE NOT NULL,
    oil_bbl DECIMAL(12,2) NOT NULL,
    gas_mcf DECIMAL(12,2),
    water_bbl DECIMAL(12,2),
    downtime_hours DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE field_production (
    fp_id SERIAL PRIMARY KEY,
    field_id INT NOT NULL REFERENCES fields(field_id),
    record_date DATE NOT NULL,
    oil_bbl DECIMAL(14,2) NOT NULL,
    gas_mcf DECIMAL(14,2),
    water_bbl DECIMAL(14,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Бурение
CREATE TABLE drilling_campaigns (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(100) NOT NULL,
    field_id INT NOT NULL REFERENCES fields(field_id),
    start_date DATE,
    end_date DATE,
    planned_wells INT,
    status VARCHAR(20) CHECK (status IN ('planned', 'in_progress', 'completed')),
    budget_usd DECIMAL(14,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drilling_operations (
    operation_id SERIAL PRIMARY KEY,
    well_id INT NOT NULL REFERENCES wells(well_id),
    campaign_id INT REFERENCES drilling_campaigns(campaign_id),
    operation_date DATE NOT NULL,
    depth_reached_m INT,
    operation_type VARCHAR(30) CHECK (operation_type IN ('spud', 'drilling', 'casing', 'cementing', 'completion', 'testing')),
    duration_hours DECIMAL(8,2),
    cost_usd DECIMAL(12,2),
    contractor VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Транспорт и хранение
CREATE TABLE pipelines (
    pipeline_id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    pipeline_type VARCHAR(30) CHECK (pipeline_type IN ('oil', 'gas', 'water', 'multiphase')),
    origin_field_id INT REFERENCES fields(field_id),
    destination VARCHAR(200),
    length_km DECIMAL(10,2),
    diameter_mm INT,
    capacity_bopd DECIMAL(12,2),
    status VARCHAR(20) CHECK (status IN ('operational', 'maintenance', 'decommissioned')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE storage_tanks (
    tank_id SERIAL PRIMARY KEY,
    tank_name VARCHAR(50) NOT NULL,
    field_id INT REFERENCES fields(field_id),
    capacity_bbl DECIMAL(14,2),
    current_level_bbl DECIMAL(14,2),
    product_type VARCHAR(30) CHECK (product_type IN ('crude', 'condensate', 'water')),
    status VARCHAR(20) CHECK (status IN ('active', 'maintenance', 'out_of_service')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Продажи
CREATE TABLE buyers (
    buyer_id SERIAL PRIMARY KEY,
    buyer_name VARCHAR(200) NOT NULL,
    country VARCHAR(50),
    contract_type VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales_contracts (
    contract_id SERIAL PRIMARY KEY,
    contract_number VARCHAR(50) UNIQUE NOT NULL,
    buyer_id INT NOT NULL REFERENCES buyers(buyer_id),
    product_type VARCHAR(30) CHECK (product_type IN ('crude', 'gas', 'condensate')),
    contract_date DATE,
    volume_bbl DECIMAL(14,2),
    price_per_bbl DECIMAL(10,2),
    delivery_point VARCHAR(200),
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) CHECK (status IN ('active', 'fulfilled', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE liftings (
    lifting_id SERIAL PRIMARY KEY,
    contract_id INT REFERENCES sales_contracts(contract_id),
    lifting_date DATE NOT NULL,
    volume_bbl DECIMAL(12,2) NOT NULL,
    quality_grade VARCHAR(20),
    loading_point VARCHAR(100),
    vessel_name VARCHAR(100),
    price_per_bbl DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Затраты
CREATE TABLE operating_costs (
    cost_id SERIAL PRIMARY KEY,
    field_id INT NOT NULL REFERENCES fields(field_id),
    cost_date DATE NOT NULL,
    cost_category VARCHAR(50) CHECK (cost_category IN ('labor', 'maintenance', 'chemicals', 'utilities', 'logistics', 'overhead', 'other')),
    amount_usd DECIMAL(14,2) NOT NULL,
    description TEXT,
    well_id INT REFERENCES wells(well_id),
    platform_id INT REFERENCES platforms(platform_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Персонал
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    position VARCHAR(100),
    department VARCHAR(100),
    field_id INT REFERENCES fields(field_id),
    platform_id INT REFERENCES platforms(platform_id),
    hire_date DATE,
    salary_usd DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Безопасность
CREATE TABLE safety_incidents (
    incident_id SERIAL PRIMARY KEY,
    field_id INT REFERENCES fields(field_id),
    platform_id INT REFERENCES platforms(platform_id),
    incident_date DATE NOT NULL,
    incident_type VARCHAR(50) CHECK (incident_type IN ('LTI', 'TRC', 'spill', 'fire', 'near_miss', 'environmental')),
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    lost_time_days INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Подрядчики
CREATE TABLE contractors (
    contractor_id SERIAL PRIMARY KEY,
    contractor_name VARCHAR(200) NOT NULL,
    specialization VARCHAR(100),
    country VARCHAR(50),
    contract_value_usd DECIMAL(14,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Геология
CREATE TABLE reservoir_data (
    data_id SERIAL PRIMARY KEY,
    field_id INT NOT NULL REFERENCES fields(field_id),
    well_id INT REFERENCES wells(well_id),
    data_date DATE NOT NULL,
    pressure_psi DECIMAL(10,2),
    temperature_c DECIMAL(5,2),
    water_cut_percent DECIMAL(5,2),
    GOR_scf_bbl DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
