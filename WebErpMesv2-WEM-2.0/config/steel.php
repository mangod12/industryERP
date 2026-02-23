<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Kumar Brothers Steel ERP Configuration
    |--------------------------------------------------------------------------
    |
    | Steel-specific settings for fabrication operations
    |
    */

    // Material density in kg/m³ for weight calculations
    'default_density' => env('STEEL_DEFAULT_DENSITY', 7850),

    // Production stages
    'production_stages' => [
        'fabrication' => [
            'name' => 'Fabrication',
            'order' => 1,
            'auto_deduct_material' => true,
        ],
        'painting' => [
            'name' => 'Painting',
            'order' => 2,
            'auto_deduct_material' => false,
        ],
        'dispatch' => [
            'name' => 'Ready for Dispatch',
            'order' => 3,
            'auto_deduct_material' => false,
        ],
    ],

    // Scrap configuration
    'scrap' => [
        'auto_classify' => env('SCRAP_AUTO_CLASSIFY', true),
        'reason_codes' => [
            'cutting_waste' => 'Cutting Waste',
            'defect' => 'Manufacturing Defect',
            'damage' => 'Handling Damage',
            'overrun' => 'Production Overrun',
            'leftover' => 'Leftover Material',
        ],
        'statuses' => [
            'pending' => 'Pending Review',
            'returned_to_inventory' => 'Returned to Inventory',
            'moved_to_reusable' => 'Moved to Reusable',
            'disposed' => 'Disposed',
            'recycled' => 'Sent to Recycler',
            'sold' => 'Sold as Scrap',
        ],
    ],

    // Reusable stock configuration
    'reusable' => [
        'min_size_mm' => env('REUSABLE_MIN_SIZE', 100),
        'quality_grades' => [
            'A' => 'Grade A - Excellent condition',
            'B' => 'Grade B - Minor surface defects',
            'C' => 'Grade C - Usable with caution',
        ],
        'match_tolerance_mm' => 10, // Tolerance for finding matching pieces
    ],

    // Common material types for steel fabrication
    'material_types' => [
        'MS Plate' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Sheet' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Angle' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Channel' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Beam' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Flat' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Round Bar' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Square Bar' => ['unit' => 'kg', 'has_dimensions' => true],
        'MS Pipe' => ['unit' => 'kg', 'has_dimensions' => true],
        'SS Plate' => ['unit' => 'kg', 'has_dimensions' => true],
        'SS Sheet' => ['unit' => 'kg', 'has_dimensions' => true],
        'GI Sheet' => ['unit' => 'kg', 'has_dimensions' => true],
        'Bolts & Nuts' => ['unit' => 'pcs', 'has_dimensions' => false],
        'Welding Rods' => ['unit' => 'kg', 'has_dimensions' => false],
        'Paint' => ['unit' => 'ltrs', 'has_dimensions' => false],
        'Primer' => ['unit' => 'ltrs', 'has_dimensions' => false],
        'Thinner' => ['unit' => 'ltrs', 'has_dimensions' => false],
    ],

    // Dimension format patterns
    'dimension_formats' => [
        'plate' => '{length}mm x {width}mm x {thickness}mm',
        'angle' => '{size}mm x {size}mm x {thickness}mm x {length}m',
        'channel' => '{size}mm x {length}m',
        'beam' => '{size}mm x {length}m',
        'pipe' => 'Ø{diameter}mm x {thickness}mm x {length}m',
        'round' => 'Ø{diameter}mm x {length}m',
    ],

    // Loss analytics thresholds
    'analytics' => [
        'scrap_rate_warning' => 5, // Percentage
        'scrap_rate_critical' => 10,
        'recovery_rate_target' => 95,
    ],

];
