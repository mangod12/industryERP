<?php

namespace App\Rules;

use App\Services\CompanyService;
use Illuminate\Contracts\Validation\Rule;

class ValidVatNumber implements Rule
{
    protected $vatService;

    public function __construct(CompanyService $vatService)
    {
        $this->vatService = $vatService;
    }

    /**
     * Validate the given VAT number.
     *
     * This method checks if the provided VAT number is valid. It first checks if the VAT number is empty,
     * in which case it returns true to allow nullable VAT numbers. If the VAT number is not empty, it
     * extracts the country code and the VAT number, then uses the vatService to validate the VAT number.
     *
     * @param  string  $attribute  The name of the attribute being validated.
     * @param  mixed  $value  The value of the attribute being validated.
     * @return bool  True if the VAT number is valid or empty, false otherwise.
     */
    public function passes($attribute, $value)
    {
 
        if (empty($value)) {
            return true; // Pass if the VAT number is empty (nullable case)
        }

        $countryCode = substr($value, 0, 2);
        $vatNumber = substr($value, 2);

        return $this->vatService->validateVatNumber($countryCode, $vatNumber);
    }

    public function message()
    {
        return 'The VAT number is invalid.';
    }
}
