<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Methods\MethodsServices;
use App\Models\Methods\MethodsRessources;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;

class MethodsRessourcesSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        // Retrieve the service with the code 'COMPO'
        $compoService = MethodsServices::where('code', 'COMPO')->first();

        // Check if the service exists
        if (!$compoService) {
            $this->command->error('The service with the code "COMPO" does not exist.');
            return;
        }

        // Resources to insert
        $resources = [
            ['ordre' => 1, 'code' => 'LASER_TRUMP', 'label' => 'Laser Trumpf', 'mask_time' => 2, 'capacity' => 100, 'section_id' => 1, 'color' => '#FF5733', 'comment' => 'Laser Machine'],
            ['ordre' => 2, 'code' => 'CNC_MAZAK', 'label' => 'CNC Mazak', 'mask_time' => 2, 'capacity' => 80, 'section_id' => 4, 'color' => '#33FF57', 'comment' => 'CNC Machining Center'],
            ['ordre' => 3, 'code' => 'IMPRESSION_3D', 'label' => '3D Printing', 'mask_time' => 1, 'capacity' => 60, 'section_id' => 4, 'color' => '#3357FF', 'comment' => '3D Printer'],
            ['ordre' => 4, 'code' => 'MIG_WELDING', 'label' => 'MIG Welding Station', 'mask_time' => 2, 'capacity' => 50, 'section_id' => 2, 'color' => '#FFC300', 'comment' => 'MIG Welding Station'],
            ['ordre' => 5, 'code' => 'PRESS', 'label' => 'Hydraulic Press', 'mask_time' => 2, 'capacity' => 90, 'section_id' => 3, 'color' => '#C70039', 'comment' => 'Forming Press'],
            ['ordre' => 6, 'code' => 'PLASMA_CUT', 'label' => 'Plasma Cutting', 'mask_time' => 2, 'capacity' => 85, 'section_id' => 4, 'color' => '#900C3F', 'comment' => 'Plasma Cutting'],
            ['ordre' => 7, 'code' => 'PAINT_BOOTH', 'label' => 'Paint Booth', 'mask_time' => 2, 'capacity' => 40, 'section_id' => 4, 'color' => '#581845', 'comment' => 'Industrial Paint Booth'],
            ['ordre' => 8, 'code' => 'SAND_BLAST', 'label' => 'Sandblasting', 'mask_time' => 1, 'capacity' => 70, 'section_id' => 4, 'color' => '#DAF7A6', 'comment' => 'Sandblasting Machine'],
            ['ordre' => 9, 'code' => 'WATER_JET', 'label' => 'Water Jet Cutting', 'mask_time' => 2, 'capacity' => 75, 'section_id' => 4, 'color' => '#FFC0CB', 'comment' => 'Water Jet Cutting'],
            ['ordre' => 10, 'code' => 'BENDING_MACHINE', 'label' => 'Bending Machine', 'mask_time' => 2, 'capacity' => 65, 'section_id' => 4, 'color' => '#808080', 'comment' => 'Bending Machine'],
        ];

        // Insert the resources
        foreach ($resources as $resource) {
            MethodsRessources::create(array_merge($resource, [
            'methods_services_id' => $compoService->id,
            ]));
        }

        $this->command->info('Ressources check');
    }

}
