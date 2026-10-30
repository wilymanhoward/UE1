// Last Seed - a marsh pad that slowly sinks under the ball.
//
// Purpose: the same behaviour as a crumbling platform with gentler values: a brief wobble, a slow sink, and
// a slow rise back. Place its top at the surface of an AWaterVolume.
// Design pattern: inheritance used only to change defaults, so it adds no logic.
// Connections: child of ACrumblingPlatform.

#pragma once

#include "CoreMinimal.h"
#include "CrumblingPlatform.h"
#include "SinkingPad.generated.h"

UCLASS()
class ASSIGNMENT1_API ASinkingPad : public ACrumblingPlatform
{
	GENERATED_BODY()

public:
	ASinkingPad();
};
