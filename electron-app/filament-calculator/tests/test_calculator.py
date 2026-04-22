import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import calculate_cost_details


def test_calculate_cost_details_normal():
    """Normal calculation with single filament."""
    printer = {"power_watts": 200, "depreciation_per_hour": 10}
    filament = {"spool_price": 1000, "spool_weight_g": 1000}
    filaments_data = [{"filament": filament, "weight": 100}]
    
    details = calculate_cost_details(printer, filaments_data, print_time=2, base_rate=50, markup_pct=20)
    
    # Filament cost: 100g * (1000rub/1000g) = 100 rub
    assert details["total_filament_cost"] == 100.0
    assert details["total_weight"] == 100.0
    # Electricity: 2h * 0.2kW * 5rub/kWh = 2 rub (assuming electricity_rate is fetched from DB default 5.0)
    assert "electricity_cost" in details
    # Depreciation: 2h * 10rub/h = 20 rub
    assert details["depreciation_cost"] == 20.0
    # Subtotal: 50 + 100 + 2 + 20 = 172
    assert details["subtotal"] == 172.0
    # Markup: 172 * 0.2 = 34.4
    assert details["markup_amount"] == 34.4
    # Total: 172 + 34.4 = 206.4
    assert details["total"] == 206.4
    assert len(details["filament_costs"]) == 1


def test_calculate_cost_details_zero_spool_weight():
    """Division by zero protection: spool_weight_g = 0 should not crash."""
    printer = {"power_watts": 200, "depreciation_per_hour": 10}
    filament = {"spool_price": 1000, "spool_weight_g": 0}
    filaments_data = [{"filament": filament, "weight": 100}]
    
    details = calculate_cost_details(printer, filaments_data, print_time=1, base_rate=50, markup_pct=0)
    
    # Should not crash; price_per_gram becomes 1000/1.0 = 1000
    assert details["total_filament_cost"] == 100000.0  # 100g * 1000rub/g


def test_calculate_cost_details_negative_weight():
    """Negative weight is still used in calculation (function does not validate)."""
    printer = {"power_watts": 200, "depreciation_per_hour": 10}
    filament = {"spool_price": 1000, "spool_weight_g": 1000}
    filaments_data = [{"filament": filament, "weight": -50}]
    
    details = calculate_cost_details(printer, filaments_data, print_time=1, base_rate=50, markup_pct=0)
    
    assert details["total_weight"] == -50.0
    assert details["total_filament_cost"] == -50.0


def test_calculate_cost_details_multiple_filaments():
    """Multiple filaments should be summed correctly."""
    printer = {"power_watts": 200, "depreciation_per_hour": 0}
    f1 = {"spool_price": 1000, "spool_weight_g": 1000}
    f2 = {"spool_price": 2000, "spool_weight_g": 1000}
    filaments_data = [
        {"filament": f1, "weight": 100},
        {"filament": f2, "weight": 200},
    ]
    
    details = calculate_cost_details(printer, filaments_data, print_time=0, base_rate=0, markup_pct=0)
    
    assert details["total_weight"] == 300.0
    assert details["total_filament_cost"] == 500.0  # 100 + 400
    assert len(details["filament_costs"]) == 2


def test_calculate_cost_details_boundary_print_time():
    """Very long print time (edge case)."""
    printer = {"power_watts": 200, "depreciation_per_hour": 0}
    filament = {"spool_price": 1000, "spool_weight_g": 1000}
    filaments_data = [{"filament": filament, "weight": 0}]
    
    details = calculate_cost_details(printer, filaments_data, print_time=8760, base_rate=0, markup_pct=0)
    
    # Electricity for 1 year at 200W with default rate 5.0
    assert details["electricity_cost"] == 8760.0  # 8760h * 0.2kW * 5rub/kWh
