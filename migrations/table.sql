CREATE TABLE IF NOT EXISTS location(
    city VARCHAR,
    country VARCHAR,
    code VARCHAR,
    region_code VARCHAR
)

CREATE TABLE IF NOT EXISTS proxy(
    host VARCHAR,
    port INTEGER,
    user_ VARCHAR,
    password VARCHAR,
    date_creation timestamp without time zone default (now() at time zone 'utc'),
    protocol VARCHAR(6),
    location_code VARCHAR, FOREIGN KEY (location) REFERENCES (location.code),
    latency INTEGER,
    anonymous BOOLEAN,
    is_alive BOOLEAN,
    CONSTRAINT c_host_port PRIMARY KEY(host, port)
);