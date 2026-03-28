<?php

namespace App\Services;

use DragonBe\Vies\Vies;
use DragonBe\Vies\ViesException;

class CompanyService
{
    protected $vies;

    public function __construct()
    {
        $this->vies = new Vies();
    }

    /**
     * Validates a VAT number for a given country code.
     *
     * This function uses the VIES (VAT Information Exchange System) service to validate
     * the VAT number if VAT validation is enabled via the .env configuration.
     *
     * @param string $countryCode The country code for the VAT number.
     * @param string $vatNumber The VAT number to be validated.
     * @return bool Returns true if the VAT number is valid, false otherwise.
     *              If VAT validation is disabled via .env, it returns true.
     *              If the VIES service is not available or an exception occurs, it returns false.
     * @throws ViesException If there is an error during the VAT validation process.
     */
    public function validateVatNumber($countryCode, $vatNumber)
    {      
        // Check if VAT validation is enabled via .env
        if (env('VAT_VALIDATION_ENABLED', true)) {
            try {
            // Checks if the VIES service is active
                if ($this->vies->getHeartBeat()->isAlive()) {
                    // Checks if the VIES service is active
                    $result = $this->vies->validateVat($countryCode, $vatNumber);
                    return $result->isValid();
                } else {
                    // Returns false if the service is not available
                    return false;
                }
            } catch (ViesException $viesException){
                // Handle the exception if there is a validation error (e.g. invalid country code)
                // You can either return false or handle it differently depending on your needs
                return false; 
            }
        }
        return true;
    }
}