@echo off
REM Reset vector stores script for Windows
echo Resetting vector stores...

if exist "src\stores\vector\" (
    echo Removing vector store...
    rmdir /s /q "src\stores\vector"
)

if exist "src\stores\catalog\" (
    echo Removing catalog store...
    rmdir /s /q "src\stores\catalog"
)

echo Creating fresh directories...
mkdir "src\stores\vector"
mkdir "src\stores\catalog"

echo Vector stores reset complete!
