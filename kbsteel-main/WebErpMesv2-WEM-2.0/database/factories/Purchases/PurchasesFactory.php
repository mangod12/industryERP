<?php

namespace Database\Factories\Purchases;

use App\Models\User;
use App\Models\Companies\Companies;
use App\Models\Purchases\Purchases;
use App\Models\Companies\CompaniesContacts;
use App\Models\Companies\CompaniesAddresses;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<Purchases>
 */
class PurchasesFactory extends Factory
{
    protected $model = Purchases::class;

    public function definition()
    {
        return [
            'code' => $this->faker->unique()->word,
            'label' => $this->faker->sentence,
            'companies_id' => Companies::all()->random()->id,
			'companies_contacts_id' => CompaniesContacts::all()->random()->id,
			'companies_addresses_id' => CompaniesAddresses::all()->random()->id,
            'statu' => $this->faker->numberBetween($min = 1, $max = 3),
            'user_id' => User::all()->random()->id,
            'comment'=> $this->faker->paragraphs(2, true),
        ];
    }
}
