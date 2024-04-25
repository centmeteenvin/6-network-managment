# 6-network-managment

## Prerequisites

- root privileges
- python3.10 [Ubuntu Install Guide](https://gist.github.com/rutcreate/c0041e842f858ceb455b748809763ddb)
- git

## How to use
run the following command:
```
sudo python main.py -n <nodeNr> --others <other node numbers as comma separated string>
```

Additionally we can apply the following extra parameters:
- `--level`: This sets the logging level, 'INFO' by default
- `--ap`: Indicate if the node should behave as an acces point 

### Example usage
`sudo python main.py --ap -n 24 --other "21,22,28" --level DEBUG`

### Additional information
Additional information can be found by running
```
sudo python main.py --help
```

## Updating
A simple update script `update.sh` has been provided.