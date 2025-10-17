#!/bin/bash
# Reset vector stores script for Unix/Mac
echo "Resetting vector stores..."

if [ -d "src/stores/vector" ]; then
    echo "Removing vector store..."
    rm -rf src/stores/vector/*
fi

if [ -d "src/stores/catalog" ]; then
    echo "Removing catalog store..."
    rm -rf src/stores/catalog/*
fi

echo "Vector stores reset complete!"
