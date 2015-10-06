# check_mikrotik
Nagios style check for Mikrotik Routeros

## Installation
Requires rosapi (https://github.com/jellonek/rosapi.git)
```
git clone https://github.com/jellonek/rosapi.git
cd rosapi
sudo python setup.py install
```
## Testing
```
./check_mikrotik -H 10.1.1.1 -U admin -P password
```

