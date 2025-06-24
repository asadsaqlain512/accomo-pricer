#!/bin/bash

# Accommodation Price Crawler Docker Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Function to build and start services
start_services() {
    local profile=${1:-""}
    local compose_file="docker-compose.yml"
    
    if [ "$profile" = "prod" ]; then
        compose_file="docker-compose.prod.yml"
        print_status "Starting production services..."
    elif [ "$profile" = "dev" ]; then
        print_status "Starting development services with admin interfaces..."
        docker-compose --profile dev up -d
        return
    else
        print_status "Starting services..."
    fi
    
    docker-compose -f $compose_file up -d --build
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
}

# Function to restart services
restart_services() {
    print_status "Restarting services..."
    docker-compose restart
}

# Function to show logs
show_logs() {
    local service=${1:-"accomopricer"}
    print_status "Showing logs for $service..."
    docker-compose logs -f $service
}

# Function to show status
show_status() {
    print_status "Service status:"
    docker-compose ps
}

# Function to clean up
cleanup() {
    print_warning "This will remove all containers, networks, and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Function to show help
show_help() {
    echo "Accommodation Price Crawler Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [profile]    Start services (dev/prod)"
    echo "  stop               Stop all services"
    echo "  restart            Restart all services"
    echo "  logs [service]     Show logs for a service"
    echo "  status             Show service status"
    echo "  cleanup            Remove all containers and volumes"
    echo "  help               Show this help message"
    echo ""
    echo "Profiles:"
    echo "  dev                Development mode with admin interfaces"
    echo "  prod               Production mode with security"
    echo ""
    echo "Examples:"
    echo "  $0 start dev       Start development environment"
    echo "  $0 start prod      Start production environment"
    echo "  $0 logs mongodb    Show MongoDB logs"
    echo "  $0 status          Show all service status"
}

# Main script logic
main() {
    local command=${1:-"help"}
    local option=${2:-""}
    
    case $command in
        "start")
            check_docker
            check_docker_compose
            start_services $option
            print_success "Services started successfully!"
            print_status "API available at: http://localhost:8000"
            print_status "API docs available at: http://localhost:8000/docs"
            if [ "$option" = "dev" ]; then
                print_status "MongoDB Express available at: http://localhost:8081"
                print_status "Redis Commander available at: http://localhost:8082"
            fi
            ;;
        "stop")
            stop_services
            print_success "Services stopped successfully!"
            ;;
        "restart")
            restart_services
            print_success "Services restarted successfully!"
            ;;
        "logs")
            show_logs $option
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@" 