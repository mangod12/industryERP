<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Methods\MethodsFamilies;
use App\Models\Methods\MethodsServices;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;

class MethodsFamiliesSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
            // Retrieve the service with the code 'COMPO'
            $compoService = MethodsServices::where('code', 'COMPO')->first();

            // Check that the service exists
            if (!$compoService) {
                $this->command->error('The service with the code "COMPO" does not exist.');
                return;
            }
    
            // The article families to insert
            $families = [
                ['code' => 'VIS', 'label' => 'Screws'],
                ['code' => 'TOL', 'label' => 'Sheet Metal'],
                ['code' => 'BAR', 'label' => 'Bar'],
                ['code' => 'RAC', 'label' => 'Fitting'],
                ['code' => 'TUB', 'label' => 'Tube'],
                ['code' => 'PRO', 'label' => 'Profile'],
                ['code' => 'PLA', 'label' => 'Plate'],
                ['code' => 'CAB', 'label' => 'Cable'],
                ['code' => 'ROU', 'label' => 'Bearing'],
                ['code' => 'RES', 'label' => 'Spring'],
            ];
    
            // Insert the article families with the service 'COMPO'
            foreach ($families as $family) {
                MethodsFamilies::create([
                    'code' => $family['code'],
                    'label' => $family['label'],
                    'methods_services_id' => $compoService->id,
                ]);
            }
    
            $this->command->info('Fammillies check');
    }
}
