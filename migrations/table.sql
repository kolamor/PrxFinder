CREATE TABLE IF NOT EXISTS location(
    ip INET PRIMARY KEY,
    country_name VARCHAR,
    country_code VARCHAR,
    region_code VARCHAR,
    region_name VARCHAR,
    city VARCHAR,
    time_zone VARCHAR,
    latitude FLOAT,
    longitude FLOAT,
    zip_code VARCHAR,
    metro_code INTEGER
);

CREATE TABLE IF NOT EXISTS proxy(
    host INET,
    port INTEGER,
    login VARCHAR,
    password VARCHAR,
    date_creation timestamp without time zone default (now() at time zone 'utc'),
    date_update timestamp without time zone,
    scheme VARCHAR(6),
    latency FLOAT,
    anonymous BOOLEAN,
    is_alive BOOLEAN,
    in_process BOOLEAN DEFAULT FALSE,
    CONSTRAINT c_host_port PRIMARY KEY(host, port)
);