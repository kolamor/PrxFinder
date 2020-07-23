## PostgreSQL

### Table `Proxy`
<ol>
    <li> host - varchar</li>
    <li>port - integer</li>
    <li>user - varchar </li>
    <li>password - varchar (open view?)</li>
    <li>location - referer Location</li>
    <li>checked_at - datetime</li>
    <li>schema(protocol)- (http, https, socks4, socks5)</li>
    <li>latency - int</li>
    <li>is alive - boolean</li>
    <li>anonymous - ?</li>
</ol>


### Table `Location`
<ol>
    <li>country - varchar</li>
    <li>city</li>
    <li>geo ?</li>
    <li>code - ISO country code</li>
    <li>region_code - ISO region code</li>
</ol>