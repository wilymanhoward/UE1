// See SteamVent.h for this class's purpose and connections.

#include "SteamVent.h"

#include "Components/BoxComponent.h"

ASteamVent::ASteamVent()
{
	Box->SetBoxExtent(FVector(100.f, 100.f, 400.f));
	WindDirection = FVector::UpVector;
	Strength = 1800.f;
	bPulsing = true;
}
