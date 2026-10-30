// Last Seed - engine meshes used as default visuals.
//
// Purpose: puzzle actors work as soon as they are placed, before any art exists. Replace the mesh on a
// Blueprint child at any time. Only call these from a constructor, which is where FObjectFinder is allowed.

#pragma once

#include "CoreMinimal.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

namespace LSDefaultMeshes
{
	/** A 100 cm cube with its pivot at the centre. */
	inline UStaticMesh* Cube()
	{
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Finder(TEXT("/Engine/BasicShapes/Cube.Cube"));
		return Finder.Object.Get();
	}

	/** A 100 cm wide sphere with its pivot at the centre. */
	inline UStaticMesh* Sphere()
	{
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Finder(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		return Finder.Object.Get();
	}

	/** A 100 cm cone with its pivot at the centre. */
	inline UStaticMesh* Cone()
	{
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Finder(TEXT("/Engine/BasicShapes/Cone.Cone"));
		return Finder.Object.Get();
	}
}
