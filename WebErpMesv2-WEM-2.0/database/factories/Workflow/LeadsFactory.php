<?php

namespace Database\Factories\Workflow;

use App\Models\User;
use App\Models\Workflow\Leads;
use App\Models\Companies\Companies;
use App\Models\Companies\CompaniesContacts;
use App\Models\Companies\CompaniesAddresses;
use Illuminate\Database\Eloquent\Factories\Factory;

class LeadsFactory extends Factory
{
    /**
     * The name of the factory's corresponding model.
     *
     * @var string
     */
    protected $model = Leads::class;

    /**
     * Define the model's default state.
     *
     * @return array
     */
    public function definition()
    {
        return [
            'companies_id' => Companies::all()->random()->id,  
            'companies_contacts_id' => CompaniesContacts::all()->random()->id, 
            'companies_addresses_id' => CompaniesAddresses::all()->random()->id,
            'user_id' => User::all()->random()->id,
            'statu' => $this->faker->randomElement(['1', '2', '3', '4', '5']),
            'source' => $this->faker->randomElement(['website', 'referral', 'email campaign', 'phone call']),
            'priority' => $this->faker->randomElement(['1', '2', '3']),
            'campaign' => $this->faker->word, 
            'comment' => $this->faker->paragraph, 
        ];
    }
}
