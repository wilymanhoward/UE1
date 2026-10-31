// Last Seed - shared form types.
//
// Purpose: defines the three forms the seed can take and the block of data that describes each one.
// Design pattern: data-driven design. Forms differ by the values in FSeedFormData, not by branching
// on the form type, so a new behaviour difference is usually a new field and not a new "if".
// Connections: ASeedBall owns a TMap<ESeedForm, FSeedFormData> and applies an entry when it switches form.
// Later systems (wind, water, hazards) read the current entry through ASeedBall::GetCurrentFormData().

#pragma once

#include "CoreMinimal.h"
#include "SeedFormTypes.generated.h"

class UMaterialInterface;
class UNiagaraSystem;
class UPhysicalMaterial;
class USoundBase;
class UStaticMesh;

/** The three forms of the seed. Seed is always unlocked; the others unlock through pickups. */
UENUM(BlueprintType)
enum class ESeedForm : uint8
{
	Seed,
	Stone,
	Dandelion
};

/** Everything that makes one form feel different. The default values describe the balanced Seed form. */
USTRUCT(BlueprintType)
struct FSeedFormData
{
	GENERATED_BODY()

	/** Visible mesh that rolls with the ball. It has no collision. Leave empty to show the plain physics sphere. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Assets")
	TObjectPtr<UStaticMesh> Mesh = nullptr;

	/** Material for Mesh. Leave empty to use the mesh's own material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Assets")
	TObjectPtr<UMaterialInterface> Material = nullptr;

	/** Visible mesh that stays upright while the ball rolls, such as the Seed's sprout. Model it around the ball's centre. Can be empty. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Assets")
	TObjectPtr<UStaticMesh> UprightMesh = nullptr;

	/** Material for UprightMesh. Leave empty to use the mesh's own material. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Assets")
	TObjectPtr<UMaterialInterface> UprightMaterial = nullptr;

	/** Particles that play around this form. Leave empty for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Assets")
	TObjectPtr<UNiagaraSystem> GlowEffect = nullptr;

	/** Surface friction and bounciness of this form, for example high friction for Stone on ice. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Assets")
	TObjectPtr<UPhysicalMaterial> PhysicalMaterial = nullptr;

	/** Looping sound while this form rolls. Its volume and pitch follow speed. Leave empty for no rolling sound. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Assets")
	TObjectPtr<USoundBase> RollSound = nullptr;

	/** Colour of the light this form gives off. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FLinearColor GlowColor = FLinearColor(1.f, 0.72f, 0.3f);

	/** Brightness of that light in candelas. 0 turns it off. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float GlowBrightness = 40.f;

	/** Mass in kg. Pressure plates and pushable blocks react to this value. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float MassKg = 20.f;

	/** How quickly the ball loses travel speed. Higher feels heavier in air and on slopes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float LinearDamping = 0.2f;

	/** How quickly the ball stops spinning. Higher makes it stop sooner when you release the keys. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float AngularDamping = 1.f;

	/** Rolling acceleration in radians/s^2. Mass does not change it, so it can be tuned on its own. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float TorqueStrength = 40.f;

	/** Spin speed limit in degrees/s. Top roll speed is roughly this value in radians times the ball radius. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float MaxAngularSpeed = 720.f;

	/** Upward speed in cm/s added by a jump. Jump height is roughly speed^2 / (2 * gravity). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float JumpImpulse = 700.f;

	/** Multiplier on wind force. 0.05 barely moves, 1.5 is blown around. Read by AWindVolume in Phase 3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float WindResponse = 1.f;

	/** Gravity multiplier: 1 is normal, below 1 floats, above 1 falls harder. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float GravityScale = 1.f;

	/** Floats in water when true and sinks when false. Read by AWaterVolume in Phase 3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	bool bBuoyancyEnabled = true;

	/** Any hazard kills this form instantly. Read by AHazardVolume in Phase 3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	bool bFragile = false;

	/** This form may ground-slam in the air. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	bool bCanSlam = false;

	/** This form may glide by holding jump while falling. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	bool bCanGlide = false;
};
