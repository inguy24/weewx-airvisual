#!/usr/bin/env python3

"""
WeeWX AirVisual Extension Installer - CORRECTED for WeeWX 5.1

This installer sets up the AirVisual service extension for WeeWX,
including database schema updates, configuration modifications,
and service registration with proper database field management.

Uses proper WeeWX ExtensionInstaller base class with configure method.
"""

import configobj
import os
import sys
import subprocess
import weewx.manager
import weedb
from weecfg.extension import ExtensionInstaller

# WeeWX extension info
EXTENSION_NAME = 'AirVisual'
EXTENSION_VERSION = '1.0.0'
EXTENSION_DESCRIPTION = 'Air quality data from IQ Air AirVisual API'

def loader():
    """Return installer object."""
    return AirVisualInstaller()

class AirVisualInstaller(ExtensionInstaller):
    """WeeWX extension installer for AirVisual service with proper database management."""
    
    def __init__(self):
        super(AirVisualInstaller, self).__init__(
            version=EXTENSION_VERSION,
            name=EXTENSION_NAME,
            description=EXTENSION_DESCRIPTION,
            author="WeeWX Community",
            author_email="",
            files=[
                ('bin/user', ['bin/user/airvisual.py'])
            ],
            config={
                'AirVisualService': {
                    'enable': True,
                    'api_key': 'REPLACE_ME',
                    'interval': 600,
                    'timeout': 30,
                    'log_success': False,
                    'log_errors': True,
                    'retry_wait_base': 600,
                    'retry_wait_max': 21600,
                    'retry_multiplier': 2.0
                },
                'Engine': {
                    'Services': {
                        'data_services': 'user.airvisual.AirVisualService'
                    }
                }
            }
        )
        
        self.required_fields = {
            'aqi': 'REAL',
            'main_pollutant': 'VARCHAR(10)', 
            'aqi_level': 'VARCHAR(30)'
        }
    
    def configure(self, engine):
        """Configure the extension during installation."""
        print(f"Installing {EXTENSION_NAME} extension v{EXTENSION_VERSION}")
        
        # Get configuration
        config_dict = engine.config_dict
        
        # Check and add database schema fields
        self._extend_database_schema(config_dict)
        
        # Configure the service interactively
        self._configure_service_interactive(config_dict)
        
        # Register service in Engine services
        self._register_service(config_dict)
        
        # Setup unit system
        self._setup_unit_system()
        
        print("\n" + "="*60)
        print("AirVisual extension configured successfully!")
        print("="*60)
        print("\nIMPORTANT: You must restart WeeWX for changes to take effect.")
        print("   sudo systemctl restart weewx")
        print("\nThe extension will read your station coordinates from [Station]")
        print("and collect air quality data according to your configured interval.")
        print("\nNew database fields available:")
        print("   - aqi (Air Quality Index 0-500+)")
        print("   - main_pollutant (PM2.5, PM10, Ozone, etc.)")
        print("   - aqi_level (Good, Moderate, Unhealthy, etc.)")
        
        return True
    
    def _extend_database_schema(self, config_dict):
        """Add AirVisual fields to database schema using proper WeeWX methods."""
        print("\n" + "="*60)
        print("DATABASE SCHEMA MANAGEMENT")
        print("="*60)
        print("Checking and extending database schema...")
        
        try:
            # Get database manager
            db_binding = config_dict.get('DatabaseTypes', {}).get('archive_mysql', {}).get('binding') or 'wx_binding'
            
            # Check which fields already exist and which need to be added
            existing_fields, missing_fields = self._check_existing_fields(config_dict, db_binding)
            
            if existing_fields:
                print("\nFields already present in database:")
                for field in existing_fields:
                    print(f"  ✓ {field} - already exists, skipping")
            
            if missing_fields:
                print("\nAdding missing fields to database:")
                self._add_missing_fields(config_dict, db_binding, missing_fields)
            else:
                print("\n✓ All required fields already exist in database")
            
            print("\n✓ Database schema management completed successfully")
            
        except Exception as e:
            print(f"\n❌ Error during database schema management: {e}")
            print("Installation will continue, but you may need to manually add database fields:")
            print("   weectl database add-column aqi --type 'REAL'")
            print("   weectl database add-column main_pollutant --type 'VARCHAR(10)'")
            print("   weectl database add-column aqi_level --type 'VARCHAR(30)'")
    
    def _check_existing_fields(self, config_dict, db_binding):
        """Check which required fields already exist in the database."""
        existing_fields = []
        missing_fields = []
        
        try:
            # Open database manager to check schema
            with weewx.manager.open_manager_with_config(config_dict, db_binding) as dbmanager:
                # Get current schema
                schema_columns = []
                for column in dbmanager.connection.genSchemaOf('archive'):
                    schema_columns.append(column[1])  # column[1] is the column name
                
                # Check each required field
                for field_name in self.required_fields:
                    if field_name in schema_columns:
                        existing_fields.append(field_name)
                    else:
                        missing_fields.append(field_name)
                        
        except Exception as e:
            print(f"Warning: Could not check database schema: {e}")
            # Assume all fields are missing if we can't check
            missing_fields = list(self.required_fields.keys())
        
        return existing_fields, missing_fields
    
    def _add_missing_fields(self, config_dict, db_binding, missing_fields):
        """Add missing fields to the database using weectl database add-column."""
        
        # Find weectl executable
        weectl_path = self._find_weectl()
        if not weectl_path:
            raise Exception("Could not find weectl executable. Please add fields manually.")
        
        # Get config file path
        config_path = getattr(config_dict, 'filename', '/etc/weewx/weewx.conf')
        
        for field_name in missing_fields:
            field_type = self.required_fields[field_name]
            
            print(f"  Adding field '{field_name}' ({field_type})...")
            
            # Build weectl command
            cmd = [
                weectl_path, 'database', 'add-column', field_name,
                '--type', field_type,
                '--config', config_path,
                '--binding', db_binding,
                '-y'  # Don't prompt for confirmation
            ]
            
            try:
                # Run weectl database add-column command
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"    ✓ Successfully added '{field_name}'")
                else:
                    # Check if error is due to field already existing
                    if 'duplicate column' in result.stderr.lower() or 'already exists' in result.stderr.lower():
                        print(f"    ✓ Field '{field_name}' already exists")
                    else:
                        print(f"    ❌ Failed to add '{field_name}': {result.stderr.strip()}")
                        raise Exception(f"weectl command failed: {result.stderr}")
                        
            except subprocess.TimeoutExpired:
                raise Exception(f"Timeout adding field '{field_name}' - database may be locked")
            except Exception as e:
                raise Exception(f"Error adding field '{field_name}': {e}")
    
    def _find_weectl(self):
        """Find the weectl executable."""
        # Common locations for weectl
        possible_paths = [
            '/usr/bin/weectl',
            '/usr/local/bin/weectl', 
            os.path.expanduser('~/weewx-data/bin/weectl'),
            'weectl'  # In PATH
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        # Try to find it in PATH
        try:
            result = subprocess.run(['which', 'weectl'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        
        return None
    
    def _setup_unit_system(self):
        """Setup unit system mappings for AQI fields."""
        try:
            import weewx.units
            
            # Observation to unit group mapping
            weewx.units.obs_group_dict['aqi'] = 'group_aqi'
            weewx.units.obs_group_dict['main_pollutant'] = 'group_count'
            weewx.units.obs_group_dict['aqi_level'] = 'group_count'
            
            # Unit definitions for all unit systems
            weewx.units.USUnits['group_aqi'] = 'aqi'
            weewx.units.MetricUnits['group_aqi'] = 'aqi'  
            weewx.units.MetricWXUnits['group_aqi'] = 'aqi'
            
            # Display formatting
            weewx.units.default_unit_format_dict['aqi'] = '%.0f'
            weewx.units.default_unit_label_dict['aqi'] = ' AQI'
            
            print("  ✓ Unit system mappings configured")
            
        except Exception as e:
            print(f"  Warning: Could not setup unit system: {e}")
    
    def _configure_service_interactive(self, config_dict):
        """Configure the AirVisual service settings interactively."""
        print("\n" + "="*60)
        print("SERVICE CONFIGURATION")
        print("="*60)
        print("Configuring AirVisual service...")
        
        # Get API key from user
        api_key = self._prompt_for_api_key()
        
        # Get update interval from user  
        interval = self._prompt_for_interval()
        
        # Update the config dictionary
        if 'AirVisualService' not in config_dict:
            config_dict['AirVisualService'] = {}
            
        config_dict['AirVisualService'].update({
            'api_key': api_key,
            'interval': interval
        })
        
        print(f"  ✓ API key configured")
        print(f"  ✓ Update interval: {interval} seconds ({interval//60} minutes)")
        print(f"  ✓ Retry logic: exponential backoff with indefinite retries")
    
    def _prompt_for_api_key(self):
        """Prompt user for IQ Air API key."""
        print("\n" + "-"*40)
        print("API KEY SETUP")
        print("-"*40)
        print("You need a free IQ Air API key to use this extension.")
        print("Get one at: https://www.iqair.com/dashboard/api")
        print("(Sign up for the free Community plan - 10,000 calls/month)")
        print()
        
        while True:
            api_key = input("Enter your IQ Air API key: ").strip()
            if api_key:
                # Basic validation - API keys are typically alphanumeric
                if len(api_key) >= 10 and api_key.replace('-', '').replace('_', '').isalnum():
                    confirm = input(f"Confirm API key '{api_key}'? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        return api_key
                    else:
                        continue
                else:
                    print("API key seems invalid. Please check and try again.")
            else:
                print("API key is required. Please enter a valid key.")
    
    def _prompt_for_interval(self):
        """Prompt user for data collection interval."""
        print("\n" + "-"*40)
        print("DATA COLLECTION INTERVAL")
        print("-"*40)
        print("How often should we collect air quality data?")
        print("Recommendation: 10-15 minutes (API allows 10,000 calls/month)")
        print("More frequent updates use your API quota faster.")
        print()
        
        while True:
            try:
                minutes = input("Enter interval in minutes [10]: ").strip()
                if not minutes:
                    minutes = "10"
                
                interval_minutes = int(minutes)
                if interval_minutes < 5:
                    print("Minimum interval is 5 minutes to respect API rate limits.")
                    continue
                elif interval_minutes < 10:
                    confirm = input(f"Warning: {interval_minutes} minutes may use API quota quickly. Continue? (y/n): ")
                    if confirm.strip().lower() not in ['y', 'yes']:
                        continue
                
                interval_seconds = interval_minutes * 60
                return interval_seconds
                
            except ValueError:
                print("Please enter a valid number of minutes.")
    
    def _register_service(self, config_dict):
        """Register AirVisual service in the WeeWX engine."""
        print("\n" + "="*60)
        print("SERVICE REGISTRATION")
        print("="*60)
        print("Registering service in WeeWX engine...")
        
        # Ensure Engine section exists
        if 'Engine' not in config_dict:
            config_dict['Engine'] = {}
        if 'Services' not in config_dict['Engine']:
            config_dict['Engine']['Services'] = {}
        
        # Get current data_services list
        services = config_dict['Engine']['Services']
        current_data_services = services.get('data_services', '')
        
        # Convert to list for manipulation
        if isinstance(current_data_services, str):
            data_services_list = [s.strip() for s in current_data_services.split(',') if s.strip()]
        else:
            data_services_list = list(current_data_services) if current_data_services else []
        
        # Add our service if not already present
        airvisual_service = 'user.airvisual.AirVisualService'
        if airvisual_service not in data_services_list:
            # Add to the end of data_services list
            data_services_list.append(airvisual_service)
            
            # Update configuration
            services['data_services'] = ', '.join(data_services_list)
            print(f"  ✓ Added {airvisual_service} to data_services")
        else:
            print(f"  ✓ {airvisual_service} already registered")


def main():
    """Command line installer for testing."""
    print("AirVisual Extension Installer Test")
    print("(In production, this runs via 'weectl extension install')")
    
    # Mock engine for testing
    class MockEngine:
        def __init__(self):
            self.config_dict = configobj.ConfigObj()
            self.config_dict.filename = '/etc/weewx/weewx.conf'  # Mock config path
            self.config_dict.update({
                'Station': {
                    'latitude': 33.656914792603196,
                    'longitude': -117.98254180962857
                },
                'Engine': {
                    'Services': {
                        'data_services': 'weewx.engine.StdConvert, weewx.engine.StdCalibrate, weewx.engine.StdQC'
                    }
                },
                'DataBindings': {
                    'wx_binding': {
                        'database': 'archive_sqlite',
                        'table_name': 'archive',
                        'manager': 'weewx.manager.DaySummaryManager'
                    }
                },
                'Databases': {
                    'archive_sqlite': {
                        'database_name': 'weewx.sdb',
                        'driver': 'weedb.sqlite'
                    }
                }
            })
    
    installer = loader()
    engine = MockEngine()
    
    try:
        installer.configure(engine)
        print("\n" + "="*60)
        print("TEST INSTALLATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("Final configuration:")
        if 'AirVisualService' in engine.config_dict:
            print(f"  API Key: {engine.config_dict['AirVisualService']['api_key']}")
            print(f"  Interval: {engine.config_dict['AirVisualService']['interval']} seconds")
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user.")
    except Exception as e:
        print(f"\nInstallation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()