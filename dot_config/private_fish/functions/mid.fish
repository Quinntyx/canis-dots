function mid
    ddcutil setvcp 10 50 --display 1 &
    ddcutil setvcp 10 50 --display 2 &
    wait
end