function quitwine --wraps wineserver --description "Kill all Wine processes"
    wineserver -k && pkill -9 \.exe
end