// Last Seed - a pulsing column of steam.
//
// Purpose: a wind volume set up as a tall updraft. Assign the steam effect to its Particles component.
// Design pattern: inheritance used only to change defaults, so it adds no logic.
// Connections: child of AWindVolume.

#pragma once

#include "CoreMinimal.h"
#include "WindVolume.h"
#include "SteamVent.generated.h"

UCLASS()
class ASSIGNMENT1_API ASteamVent : public AWindVolume
{
	GENERATED_BODY()

public:
	ASteamVent();
};
