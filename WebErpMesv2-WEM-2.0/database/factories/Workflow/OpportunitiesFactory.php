<?php

namespace Database\Factories\Workflow;

use App\Models\User;
use Illuminate\Support\Str;
use App\Models\Workflow\Leads;
use App\Models\Companies\Companies;
use App\Models\Workflow\Opportunities;
use App\Models\Companies\CompaniesContacts;
use App\Models\Companies\CompaniesAddresses;
use Illuminate\Database\Eloquent\Factories\Factory;

class OpportunitiesFactory extends Factory
{
    protected $model = Opportunities::class;

    public function definition()
    {

        return [
            'uuid' => Str::uuid(),
            'companies_id' => Companies::all()->random()->id,  
            'companies_contacts_id' => CompaniesContacts::all()->random()->id, 
            'companies_addresses_id' => CompaniesAddresses::all()->random()->id,
            'user_id' => User::all()->random()->id,
            'leads_id' => Leads::inRandomOrder()->first()->id ?? null,  // Lier un lead aléatoire
            'label' => $this->faker->sentence,
            'budget' => $this->faker->randomFloat(2, 1000, 100000),  // Générer un budget aléatoire
            'close_date' => $this->faker->date(),
            'statu' => $this->faker->randomElement(['1', '2', '3', '4', '5', '6']),  // Statut aléatoire
            'probality' => $this->faker->randomFloat(2, 0, 100),  // Probabilité entre 0 et 100
            'comment' => $this->faker->paragraph,
        ];
    }
}
