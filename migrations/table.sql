CREATE TABLE IF NOT EXISTS location(
    ip INET PRIMARY KEY,
    country_name VARCHAR,
    country_code VARCHAR,
    region_code VARCHAR,
    city VARCHAR,
    time_zone VARCHAR,
    latitude FLOAT,
    longitude FLOAT,
    metro_code VARCHAR
);

CREATE TABLE IF NOT EXISTS proxy(
    host INET,
    port INTEGER,
    login VARCHAR,
    password VARCHAR,
    date_creation timestamp without time zone default (now() at time zone 'utc'),
    scheme VARCHAR(6),
    latency FLOAT,
    anonymous BOOLEAN,
    is_alive BOOLEAN,
    in_process BOOLEAN,
    CONSTRAINT c_host_port PRIMARY KEY(host, port)
);