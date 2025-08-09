# Resource and City Management Commands

## Overview
Added comprehensive resource and city management commands to the Discord Hegemony Bot. Players can now transfer resources, manage cities, and admins have tools to modify player assets.

## New Commands Added (11 total)

### Resource Management Commands

#### `/add_resources` (Admin)
- **Purpose**: Add resources to any player
- **Parameters**: 
  - `player`: Target player
  - `gold`: Amount of gold to add (optional)
  - `gems`: Amount of gems to add (optional) 
  - `population`: Amount of population to add (optional)
- **Features**: Shows current resources after addition

#### `/set_resources` (Admin)
- **Purpose**: Set a player's resources to specific amounts
- **Parameters**:
  - `player`: Target player
  - `gold`: Gold amount to set (optional)
  - `gems`: Gems amount to set (optional)
  - `population`: Population amount to set (optional)
- **Features**: Shows before/after comparison

#### `/transfer_resources`
- **Purpose**: Transfer resources between players
- **Parameters**:
  - `recipient`: Player to transfer to
  - `gold`: Gold to transfer (optional)
  - `gems`: Gems to transfer (optional)
  - `population`: Population to transfer (optional)
- **Features**: 
  - Validates sufficient resources
  - Shows remaining resources after transfer
  - Prevents self-transfers

#### `/view_resources`
- **Purpose**: View detailed resource information
- **Parameters**: `player` (optional, defaults to self)
- **Features**:
  - Current resources (gold, gems, population)
  - Income/expense breakdown per turn
  - Net income calculation
  - Capacity information (brigades/generals)

### City Management Commands

#### `/add_city` (Admin)
- **Purpose**: Grant a city to a player
- **Parameters**:
  - `player`: Target player
  - `city_name`: Name of the city
  - `tier`: City tier (1-3)
  - `location`: City location (optional)
- **Features**: 
  - Automatically updates brigade cap
  - Shows tier benefits

#### `/remove_city` (Admin)
- **Purpose**: Remove a city from a player
- **Parameters**:
  - `player`: Target player
  - `city_name`: Name of city to remove
- **Features**: Updates brigade cap after removal

#### `/list_cities`
- **Purpose**: View all cities owned by a player
- **Parameters**: `player` (optional, defaults to self)
- **Features**:
  - Shows city tiers and locations
  - Displays siege status
  - Shows garrison information
  - Calculates total brigade cap bonus

#### `/upgrade_city` (Admin)
- **Purpose**: Change a city's tier
- **Parameters**:
  - `player`: City owner
  - `city_name`: Name of city to upgrade/downgrade
  - `new_tier`: New tier (1-3)
- **Features**: 
  - Shows tier change visualization
  - Updates brigade cap automatically

#### `/siege_city`
- **Purpose**: Lay siege to an enemy city
- **Parameters**:
  - `army_id`: Attacking army
  - `city_name`: Target city name
  - `target_player`: City owner
- **Features**:
  - Validates army ownership and location
  - Integrates with siege system
  - Shows siege duration and garrison info

#### `/garrison_city`
- **Purpose**: Move brigades to garrison a city
- **Parameters**:
  - `city_name`: Your city to garrison
  - `brigade_ids`: Comma-separated brigade IDs
- **Features**:
  - Validates brigade ownership
  - Prevents garrisoning army brigades
  - Shows updated garrison status

#### `/ungarrison_city`
- **Purpose**: Remove brigades from city garrison
- **Parameters**:
  - `city_name`: Your city to ungarrison
  - `brigade_ids`: Brigade IDs or "all"
- **Features**:
  - Supports removing all brigades at once
  - Returns brigades to individual control

## Integration Features

### Automatic Brigade Cap Calculation
- Cities provide brigade capacity based on tier:
  - Tier 1: +1 brigade cap
  - Tier 2: +3 brigade cap  
  - Tier 3: +5 brigade cap
- Automatically recalculated when cities are added/removed/upgraded

### Resource Economics
- **Income Sources**: Cities (5 gold each per turn)
- **Expenses**: Brigades (2 gold each), Generals (1 gold each)
- **Net Income**: Automatically calculated and displayed

### Siege Integration
- City sieges use existing siege system
- Combat Engineers enhancement reduces siege time
- Garrison brigades participate in siege defense

### Data Validation
- All commands validate player registration
- Resource transfers check sufficient funds
- City operations verify ownership
- Brigade assignments prevent conflicts

## Admin vs Player Commands

### Admin Commands (6)
- `/add_resources` - Grant resources
- `/set_resources` - Set specific amounts
- `/add_city` - Grant cities
- `/remove_city` - Remove cities
- `/upgrade_city` - Change city tiers
- `/update_brigade_cap` - Recalculate caps

### Player Commands (5)
- `/transfer_resources` - Trade with others
- `/view_resources` - Check status
- `/list_cities` - View cities
- `/siege_city` - Attack cities
- `/garrison_city` - Defend cities
- `/ungarrison_city` - Move brigades

## Technical Implementation

### Type Safety
- Uses `Optional[discord.Member]` for optional player parameters
- Validates all inputs before processing
- Proper error handling for edge cases

### Database Integration
- Seamlessly integrates with existing JSON data manager
- Updates multiple data structures consistently
- Maintains data integrity across operations

### UI/UX Features
- Rich embed displays with color coding
- Clear before/after status comparisons
- Comprehensive field information
- Error messages for invalid operations

## Testing Status
- ✅ Bot starts with 38 total commands (11 new)
- ✅ All commands registered successfully
- ✅ Type annotations properly handled
- ✅ Integration with existing systems verified

The Discord bot now has comprehensive resource and city management capabilities, allowing both players and administrators to fully control the economic and territorial aspects of the warfare game.
