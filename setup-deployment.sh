#!/bin/bash
# AuthVision Deployment Setup Script (Linux/Mac)
# Run this script on each deployment PC to configure JWT secret

echo "========================================"
echo "  AuthVision 5G Lab - Deployment Setup  "
echo "========================================"
echo ""

CURRENT_SECRET="${MAIN_BACKEND_JWT_SECRET}"

if [ ! -z "$CURRENT_SECRET" ]; then
    echo "Current JWT_SECRET is set: ${CURRENT_SECRET:0:10}..."
    read -p "Do you want to change it? (y/n): " choice
    if [ "$choice" != "y" ]; then
        echo "Keeping existing secret."
        exit 0
    fi
fi

echo ""
echo "Choose an option:"
echo "1. Generate a new secure JWT secret (for first deployment)"
echo "2. Enter an existing JWT secret (for multi-PC deployment)"
echo ""

read -p "Enter option (1 or 2): " option

if [ "$option" == "1" ]; then
    # Generate new secret
    NEW_SECRET=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=')
    
    echo ""
    echo "Generated new JWT secret:"
    echo "$NEW_SECRET"
    echo ""
    echo "IMPORTANT: Save this secret! You'll need it for other PCs."
    echo ""
    
    read -p "Set this as JWT_SECRET? (y/n): " confirm
    if [ "$confirm" == "y" ]; then
        export MAIN_BACKEND_JWT_SECRET="$NEW_SECRET"
        echo "export MAIN_BACKEND_JWT_SECRET=\"$NEW_SECRET\"" >> ~/.bashrc
        echo "JWT_SECRET set successfully!"
        echo ""
        echo "Copy this secret for other PCs:"
        echo "$NEW_SECRET"
    fi
    
elif [ "$option" == "2" ]; then
    # Enter existing secret
    echo ""
    echo "Enter the JWT secret from your main deployment PC:"
    read -p "JWT_SECRET: " EXISTING_SECRET
    
    if [ ! -z "$EXISTING_SECRET" ]; then
        export MAIN_BACKEND_JWT_SECRET="$EXISTING_SECRET"
        echo "export MAIN_BACKEND_JWT_SECRET=\"$EXISTING_SECRET\"" >> ~/.bashrc
        echo ""
        echo "JWT_SECRET set successfully!"
        echo "This PC will now be able to validate tokens from other PCs."
    else
        echo "No secret entered. Exiting."
        exit 1
    fi
else
    echo "Invalid option. Exiting."
    exit 1
fi

echo ""
echo "========================================"
echo "Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Start backend: python -m main_backend"
echo "2. Start model service: python -m model_service"
echo "3. Start frontend: cd Authvision_Frontend; npm run dev"
echo "========================================"
